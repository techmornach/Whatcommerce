"""
Tool implementations for the WhatsApp store manager (called via OpenAI function calling).
All mutations commit so follow-up tool calls see fresh data.
"""

import json
import logging
from typing import Any

from openai import OpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Order, OrderLine, Product, Tenant
from app.models.enums import OrderStatus
from app.services.product_image_storage import (
    generate_catalog_description,
    resolve_tenant_image_file,
)
from app.services.store_context import StoreContext

logger = logging.getLogger(__name__)

_MAX_DESC = 10_000
_MAX_IMAGE_URLS = 20


def _opt_nonneg_int(v: Any, *, max_v: int = 1_000_000_000) -> int | None:
    if v is None:
        return None
    try:
        x = int(v)
        if 0 <= x <= max_v:
            return x
    except (TypeError, ValueError):
        pass
    return None


def _parse_image_urls(v: Any) -> list[str] | None:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        return [s[:2048]]
    if isinstance(v, list):
        out: list[str] = []
        for x in v[:_MAX_IMAGE_URLS]:
            s = str(x).strip()
            if s:
                out.append(s[:2048])
        return out or None
    return None


def _product_count(db: Session, tenant_id: int) -> int:
    n = db.execute(
        select(func.count()).select_from(Product).where(Product.tenant_id == tenant_id)
    ).scalar()
    return int(n or 0)


def execute_store_tool(
    db: Session, ctx: StoreContext, name: str, arguments: str | dict[str, Any] | None
) -> str:
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments) if (arguments or "").strip() else {}
        except json.JSONDecodeError:
            return json.dumps({"ok": False, "error": "invalid_json_arguments"})
    else:
        args = arguments or {}
    if not isinstance(args, dict):
        return json.dumps({"ok": False, "error": "arguments_must_be_object"})

    out: dict[str, Any]
    if name == "get_store_summary":
        out = _tool_get_store_summary(db, ctx)
    elif name == "list_products":
        out = _tool_list_products(db, ctx, bool(args.get("include_inactive")))
    elif name == "add_product":
        out = _tool_add_product(
            db,
            ctx,
            str(args.get("name") or "").strip(),
            int(args.get("price_ngn") or 0),
            int(args.get("stock") or 0),
            cost_price_ngn=_opt_nonneg_int(args.get("cost_price_ngn")),
            description=args.get("description"),
            image_urls=_parse_image_urls(args.get("image_urls")),
        )
    elif name == "update_product":
        out = _tool_update_product(db, ctx, args)
    elif name == "delete_product":
        out = _tool_delete_product(db, ctx, int(args.get("product_id") or 0))
    elif name == "list_orders":
        out = _tool_list_orders(db, ctx, int(args.get("limit") or 10))
    elif name == "create_order":
        out = _tool_create_order(
            db,
            ctx,
            args.get("lines") or [],
            args.get("notes"),
            customer_name=args.get("customer_name"),
            customer_phone=args.get("customer_phone"),
        )
    elif name == "describe_product_image":
        pid = int(args.get("product_id") or 0)
        out = _tool_describe_product_image(
            db,
            ctx,
            str(args.get("image_url") or "").strip() or None,
            pid if pid > 0 else None,
        )
    elif name == "search_platform_knowledge":
        from app.services.knowledge_rag import search_knowledge_response_json

        return search_knowledge_response_json(
            db, str(args.get("query") or "").strip()
        )
    else:
        out = {"ok": False, "error": f"unknown_tool_{name}"}
    return json.dumps(out, default=str)


def _tool_get_store_summary(db: Session, ctx: StoreContext) -> dict[str, Any]:
    n_products = _product_count(db, ctx.tenant_id)
    n_orders = int(
        db.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.tenant_id == ctx.tenant_id)
        ).scalar()
        or 0
    )
    tenant = db.get(Tenant, ctx.tenant_id)
    sub = None
    if tenant and tenant.subscription_ends_at:
        sub = tenant.subscription_ends_at.isoformat()
    return {
        "ok": True,
        "business_name": ctx.business_name,
        "plan": ctx.plan_name,
        "max_products": ctx.max_products,
        "product_count": n_products,
        "order_count": n_orders,
        "subscription_ends_at": sub,
    }


def _tool_list_products(
    db: Session, ctx: StoreContext, include_inactive: bool
) -> dict[str, Any]:
    q = select(Product).where(Product.tenant_id == ctx.tenant_id).order_by(Product.id.desc())
    if not include_inactive:
        q = q.where(Product.is_active.is_(True))
    rows = list(db.execute(q).scalars().all())
    items = [
        {
            "id": p.id,
            "name": p.name,
            "price_ngn": p.price_ngn,
            "cost_price_ngn": p.cost_price_ngn,
            "stock": p.stock,
            "description": (p.description or "")[:500] if p.description else None,
            "image_urls": p.image_urls if p.image_urls else [],
            "is_active": p.is_active,
        }
        for p in rows
    ]
    return {"ok": True, "count": len(items), "products": items}


def _tool_add_product(
    db: Session,
    ctx: StoreContext,
    name: str,
    price_ngn: int,
    stock: int,
    *,
    cost_price_ngn: int | None = None,
    description: Any = None,
    image_urls: list[str] | None = None,
) -> dict[str, Any]:
    if len(name) < 2 or len(name) > 500:
        return {"ok": False, "error": "name must be 2–500 characters"}
    if price_ngn < 0 or price_ngn > 1_000_000_000:
        return {"ok": False, "error": "invalid selling price (price_ngn)"}
    if stock < 0 or stock > 1_000_000_000:
        return {"ok": False, "error": "invalid stock"}
    desc = str(description).strip()[:_MAX_DESC] if description is not None else None
    if desc == "":
        desc = None
    if _product_count(db, ctx.tenant_id) >= ctx.max_products:
        return {
            "ok": False,
            "error": f"Product limit reached ({ctx.max_products} for your plan).",
        }
    p = Product(
        tenant_id=ctx.tenant_id,
        name=name,
        price_ngn=price_ngn,
        cost_price_ngn=cost_price_ngn,
        stock=stock,
        description=desc,
        image_urls=image_urls,
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "ok": True,
        "product": {
            "id": p.id,
            "name": p.name,
            "price_ngn": p.price_ngn,
            "cost_price_ngn": p.cost_price_ngn,
            "stock": p.stock,
            "description": p.description,
            "image_urls": p.image_urls or [],
        },
    }


def _tool_update_product(
    db: Session,
    ctx: StoreContext,
    args: dict[str, Any],
) -> dict[str, Any]:
    product_id = int(args.get("product_id") or 0)
    if product_id <= 0:
        return {"ok": False, "error": "product_id required"}
    p = (
        db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == ctx.tenant_id,
            )
        )
        .scalars()
        .first()
    )
    if p is None:
        return {"ok": False, "error": "product not found"}
    if "name" in args and args.get("name") is not None:
        nm = str(args.get("name") or "").strip()
        if len(nm) < 2:
            return {"ok": False, "error": "name must be at least 2 characters if set"}
        p.name = nm
    if "price_ngn" in args and args.get("price_ngn") is not None:
        price_ngn = int(args["price_ngn"])
        if price_ngn < 0:
            return {"ok": False, "error": "invalid price"}
        p.price_ngn = price_ngn
    if "cost_price_ngn" in args:
        v = args.get("cost_price_ngn")
        if v is None:
            p.cost_price_ngn = None
        else:
            c = _opt_nonneg_int(v)
            if c is None:
                return {"ok": False, "error": "invalid cost_price_ngn"}
            p.cost_price_ngn = c
    if "description" in args:
        d = str(args.get("description") or "").strip()[:_MAX_DESC]
        p.description = d or None
    if "image_urls" in args:
        p.image_urls = _parse_image_urls(args.get("image_urls"))
    if "stock" in args and args.get("stock") is not None:
        stock = int(args["stock"])
        if stock < 0:
            return {"ok": False, "error": "invalid stock"}
        p.stock = stock
    if "is_active" in args and isinstance(args.get("is_active"), bool):
        p.is_active = bool(args.get("is_active"))
    db.add(p)
    db.commit()
    return {
        "ok": True,
        "product": {
            "id": p.id,
            "name": p.name,
            "price_ngn": p.price_ngn,
            "cost_price_ngn": p.cost_price_ngn,
            "stock": p.stock,
            "description": p.description,
            "image_urls": p.image_urls or [],
            "is_active": p.is_active,
        },
    }


def _tool_delete_product(db: Session, ctx: StoreContext, product_id: int) -> dict[str, Any]:
    if product_id <= 0:
        return {"ok": False, "error": "product_id required"}
    p = (
        db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == ctx.tenant_id,
            )
        )
        .scalars()
        .first()
    )
    if p is None:
        return {"ok": False, "error": "product not found"}
    db.delete(p)
    db.commit()
    return {"ok": True, "deleted_id": product_id}


def _tool_describe_product_image(
    db: Session,
    ctx: StoreContext,
    image_url: str | None,
    product_id: int | None,
) -> dict[str, Any]:
    """
    Vision-based catalog blurb for an image stored under this tenant's /files/products/...
    or the first image on a product row.
    """
    settings = get_settings()
    if not (settings.openai_api_key or "").strip():
        return {"ok": False, "error": "OPENAI_API_KEY not set"}

    url = (image_url or "").strip() or None
    if product_id and product_id > 0:
        p = (
            db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.tenant_id == ctx.tenant_id,
                )
            )
            .scalars()
            .first()
        )
        if p is None:
            return {"ok": False, "error": "product not found"}
        urls = list(p.image_urls or [])
        if not urls:
            return {"ok": False, "error": "product has no image_urls"}
        url = str(urls[0]).strip()
    if not url:
        return {
            "ok": False,
            "error": "Provide image_url or product_id with at least one stored image",
        }

    fp = resolve_tenant_image_file(settings, tenant_id=ctx.tenant_id, url_or_path=url)
    if fp is None:
        return {
            "ok": False,
            "error": (
                "Could not load image. Use a catalog URL from chat or this product's images."
            ),
        }

    raw = fp.read_bytes()
    mimetype = "image/jpeg"
    suf = fp.suffix.lower()
    if suf == ".png":
        mimetype = "image/png"
    elif suf == ".webp":
        mimetype = "image/webp"
    elif suf == ".gif":
        mimetype = "image/gif"

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        desc = generate_catalog_description(
            client, raw, mimetype, model=settings.openai_vision_model
        )
    except Exception as e:
        logger.exception("describe_product_image: %s", e)
        return {"ok": False, "error": f"vision_error: {e!s}"}
    return {"ok": True, "description": desc}


def _tool_list_orders(db: Session, ctx: StoreContext, limit: int) -> dict[str, Any]:
    limit = max(1, min(limit, 50))
    orders = (
        db.execute(
            select(Order)
            .where(Order.tenant_id == ctx.tenant_id)
            .order_by(Order.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    out: list[dict[str, Any]] = []
    for o in orders:
        lines = (
            db.execute(select(OrderLine).where(OrderLine.order_id == o.id))
            .scalars()
            .all()
        )
        out.append(
            {
                "id": o.id,
                "status": o.status.value,
                "total_ngn": o.total_ngn,
                "customer_name": o.customer_name,
                "customer_phone": o.customer_phone,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "lines": [
                    {
                        "product_id": li.product_id,
                        "name": li.name_snapshot,
                        "qty": li.quantity,
                        "unit_price_ngn": li.unit_price_ngn,
                    }
                    for li in lines
                ],
            }
        )
    return {"ok": True, "orders": out}


def _tool_create_order(
    db: Session,
    ctx: StoreContext,
    lines: list[dict[str, Any]],
    notes: Any,
    *,
    customer_name: Any = None,
    customer_phone: Any = None,
) -> dict[str, Any]:
    if not isinstance(lines, list) or not lines:
        return {"ok": False, "error": "lines must be a non-empty array of {product_id, quantity}"}
    parsed: list[tuple[int, int]] = []
    for li in lines:
        if not isinstance(li, dict):
            continue
        pid = int(li.get("product_id") or 0)
        qty = int(li.get("quantity") or 0)
        if pid > 0 and qty > 0:
            parsed.append((pid, qty))
    if not parsed:
        return {"ok": False, "error": "no valid lines"}

    total = 0
    line_data: list[tuple[Product, int]] = []
    for product_id, qty in parsed:
        p = (
            db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.tenant_id == ctx.tenant_id,
                    Product.is_active.is_(True),
                )
            )
            .scalars()
            .first()
        )
        if p is None:
            return {"ok": False, "error": f"product {product_id} not found or inactive"}
        if p.stock < qty:
            return {
                "ok": False,
                "error": f"Not enough stock for {p.name} (have {p.stock}, need {qty})",
            }
        total += qty * p.price_ngn
        line_data.append((p, qty))
        p.stock = p.stock - qty
        db.add(p)

    note_str = str(notes).strip()[:2000] if notes is not None else None
    cname = str(customer_name).strip()[:256] if customer_name is not None else None
    if cname == "":
        cname = None
    cphone = str(customer_phone).strip()[:64] if customer_phone is not None else None
    if cphone == "":
        cphone = None
    order = Order(
        tenant_id=ctx.tenant_id,
        status=OrderStatus.pending,
        total_ngn=total,
        notes=note_str,
        customer_name=cname,
        customer_phone=cphone,
        created_by_user_id=ctx.user_id,
    )
    db.add(order)
    db.flush()
    for p, qty in line_data:
        db.add(
            OrderLine(
                order_id=order.id,
                product_id=p.id,
                quantity=qty,
                unit_price_ngn=p.price_ngn,
                name_snapshot=p.name,
            )
        )
    db.commit()
    db.refresh(order)
    return {
        "ok": True,
        "order": {
            "id": order.id,
            "total_ngn": order.total_ngn,
            "status": order.status.value,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
        },
    }
