"""OpenAI tool implementations for LLM-driven onboarding (function calling)."""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BillingPlan, OnboardingSession, Tenant
from app.models.enums import OnboardingState, TenantStatus
from app.services.knowledge_rag import search_knowledge_response_json
from app.services.onboarding_checkout import (
    create_tenant_and_checkout,
    parse_billing_interval,
    parse_plan_key,
    valid_email,
)

logger = logging.getLogger(__name__)


def get_or_create_onboarding_session(
    db: Session, wa_chat_id: str, phone_e164: str
) -> OnboardingSession:
    s = (
        db.execute(
            select(OnboardingSession).where(
                OnboardingSession.wa_chat_id == wa_chat_id
            )
        )
        .scalars()
        .first()
    )
    if s is not None:
        return s
    other = (
        db.execute(
            select(OnboardingSession)
            .where(OnboardingSession.phone_e164 == phone_e164)
            .order_by(OnboardingSession.id.desc())
        )
        .scalars()
        .first()
    )
    if other is not None and other.wa_chat_id != wa_chat_id:
        other.wa_chat_id = wa_chat_id
        db.add(other)
        db.commit()
        db.refresh(other)
        return other
    row = OnboardingSession(
        wa_chat_id=wa_chat_id,
        phone_e164=phone_e164,
        state=OnboardingState.ask_name,
        data={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _merge_data(session: OnboardingSession, **kwargs: object) -> None:
    session.data = {**dict(session.data or {}), **kwargs}


def sync_state_from_data(session: OnboardingSession) -> None:
    """Keep FSM state aligned for admin/DB; do not undo payment_sent or complete."""
    if session.state in (OnboardingState.payment_sent, OnboardingState.complete):
        return
    d = dict(session.data or {})
    if not d.get("full_name"):
        session.state = OnboardingState.ask_name
    elif not d.get("business_name"):
        session.state = OnboardingState.ask_business
    elif not d.get("business_address"):
        session.state = OnboardingState.ask_address
    elif not d.get("email"):
        session.state = OnboardingState.ask_email
    elif not d.get("plan_id") or not d.get("plan_key"):
        session.state = OnboardingState.ask_plan
    elif not d.get("billing_interval"):
        session.state = OnboardingState.ask_billing
    else:
        session.state = OnboardingState.ask_billing


def _plans_payload(db: Session) -> list[dict[str, Any]]:
    plans = (
        db.execute(
            select(BillingPlan)
            .where(BillingPlan.is_active.is_(True))
            .order_by(BillingPlan.display_order, BillingPlan.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "key": p.key,
            "name": p.name,
            "max_products": p.max_products,
            "price_monthly_ngn": p.price_monthly_ngn,
            "price_yearly_ngn": p.price_yearly_ngn,
        }
        for p in plans
    ]


def build_snapshot(db: Session, session: OnboardingSession) -> dict[str, Any]:
    d = dict(session.data or {})
    if d.get("plan_id") and not d.get("plan_key"):
        plan0 = db.get(BillingPlan, int(d["plan_id"]))
        if plan0:
            d = {**d, "plan_key": plan0.key}
    has_plan = bool(d.get("plan_id") or d.get("plan_key"))
    missing = [
        k
        for k in (
            "full_name",
            "business_name",
            "business_address",
            "email",
        )
        if not (d.get(k) or "").strip()
    ]
    if not has_plan:
        missing.append("plan")
    if not d.get("billing_interval"):
        missing.append("billing_interval")
    ready = not missing
    pay: dict[str, Any] = {"stage": "collecting"}
    if session.tenant_id:
        t = db.get(Tenant, session.tenant_id)
        url = d.get("paystack_authorization_url")
        if t and t.status == TenantStatus.active:
            pay = {"stage": "paid_active", "tenant_id": t.id}
        elif session.state == OnboardingState.payment_sent:
            pay = {
                "stage": "awaiting_payment",
                "paystack_authorization_url": url,
                "paystack_reference": d.get("paystack_reference"),
                "tenant_id": session.tenant_id,
            }

    return {
        "onboarding_state": str(session.state),
        "active_plans": _plans_payload(db),
        "collected": {k: d.get(k) for k in (
            "full_name",
            "business_name",
            "business_address",
            "email",
            "plan_key",
            "billing_interval",
        ) if d.get(k) is not None and str(d.get(k) or "").strip() != ""},
        "missing_fields": missing,
        "ready_for_checkout": ready,
        "payment": pay,
        "phone_e164": session.phone_e164,
    }


def execute_onboarding_tool(
    db: Session,
    *,
    session: OnboardingSession,
    name: str,
    arguments: str | dict[str, Any] | None,
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

    try:
        db.refresh(session)
    except Exception:
        pass
    sid = session.id
    s = db.get(OnboardingSession, sid)
    if s is None:
        return json.dumps({"ok": False, "error": "session_not_found"})

    if name == "get_onboarding_snapshot":
        return json.dumps(
            {"ok": True, **build_snapshot(db, s)},
            default=str,
        )

    if name == "search_platform_knowledge":
        return search_knowledge_response_json(
            db, str(args.get("query") or "").strip()
        )

    if name == "reset_onboarding":
        s.data = {}
        s.state = OnboardingState.ask_name
        s.tenant_id = None
        s.user_id = None
        db.add(s)
        db.commit()
        return json.dumps(
            {"ok": True, "message": "Onboarding reset.", **build_snapshot(db, s)},
            default=str,
        )

    if name == "save_onboarding_fields":
        d = dict(s.data or {})
        if s.state in (OnboardingState.payment_sent, OnboardingState.complete):
            return json.dumps(
                {
                    "ok": False,
                    "error": "session_locked",
                    "hint": "use snapshot; payment may already be in progress or complete.",
                }
            )
        if args.get("full_name"):
            d["full_name"] = str(args["full_name"]).strip()[:200]
        if args.get("business_name"):
            d["business_name"] = str(args["business_name"]).strip()[:200]
        if args.get("business_address"):
            d["business_address"] = str(args["business_address"]).strip()[:2000]
        if args.get("email"):
            em = str(args["email"]).strip()
            if not valid_email(em):
                return json.dumps(
                    {"ok": False, "error": "invalid_email", "email": em}
                )
            d["email"] = em.lower()[:512]
        pk = args.get("plan_key")
        if pk:
            key = parse_plan_key(str(pk))
            if not key:
                return json.dumps({"ok": False, "error": "invalid_plan_key"})
            plan = (
                db.execute(
                    select(BillingPlan).where(
                        BillingPlan.key == key,
                        BillingPlan.is_active.is_(True),
                    )
                )
                .scalars()
                .first()
            )
            if not plan:
                return json.dumps({"ok": False, "error": "plan_unavailable"})
            d["plan_key"] = key
            d["plan_id"] = plan.id
        if args.get("billing_interval"):
            bi = parse_billing_interval(str(args["billing_interval"]))
            if not bi:
                return json.dumps(
                    {"ok": False, "error": "invalid_billing_use_monthly_or_yearly"}
                )
            d["billing_interval"] = bi
        s.data = d
        sync_state_from_data(s)
        db.add(s)
        db.commit()
        return json.dumps(
            {"ok": True, "saved": True, **build_snapshot(db, s)},
            default=str,
        )

    if name == "create_paystack_checkout":
        d0 = dict(s.data or {})
        if s.state == OnboardingState.payment_sent:
            return json.dumps(
                {
                    "ok": True,
                    "already_sent": True,
                    "paystack_authorization_url": d0.get("paystack_authorization_url"),
                    **build_snapshot(db, s),
                },
                default=str,
            )
        d = dict(s.data or {})
        for req in (
            "full_name",
            "business_name",
            "business_address",
            "email",
        ):
            if not (d.get(req) or "").strip():
                return json.dumps(
                    {
                        "ok": False,
                        "error": "missing_field",
                        "field": req,
                    }
                )
        plan_id = int(d.get("plan_id") or 0)
        plan = db.get(BillingPlan, plan_id) if plan_id else None
        if not plan or not plan.is_active:
            return json.dumps(
                {"ok": False, "error": "set_plan_first", "plans": _plans_payload(db)}
            )
        interval = d.get("billing_interval") or parse_billing_interval("monthly")
        if not interval:
            return json.dumps(
                {"ok": False, "error": "set_billing_interval_monthly_or_yearly"}
            )
        d["billing_interval"] = interval
        amount = (
            plan.price_monthly_ngn
            if interval == "monthly"
            else plan.price_yearly_ngn
        )
        _merge_data(s, **d)
        try:
            url, ref, tenant_id, user_id = create_tenant_and_checkout(
                db, s, plan, amount
            )
        except ValueError as e:
            if "Already active" in str(e):
                return json.dumps(
                    {"ok": False, "error": "already_subscribed_active", "detail": str(e)}
                )
            logger.exception("checkout: %s", e)
            return json.dumps(
                {"ok": False, "error": "checkout_failed", "detail": str(e)}
            )
        except Exception as e:
            logger.exception("checkout: %s", e)
            db.rollback()
            return json.dumps({"ok": False, "error": "checkout_failed", "detail": str(e)})

        s.state = OnboardingState.payment_sent
        s.tenant_id = tenant_id
        s.user_id = user_id
        _merge_data(
            s,
            paystack_authorization_url=url,
            paystack_reference=ref,
            billing_interval=interval,
            amount_ngn=amount,
        )
        db.add(s)
        db.commit()
        return json.dumps(
            {
                "ok": True,
                "paystack_authorization_url": url,
                "paystack_reference": ref,
                "amount_ngn": amount,
                "plan_name": plan.name,
                "billing_interval": interval,
                **build_snapshot(db, s),
            },
            default=str,
        )

    return json.dumps({"ok": False, "error": f"unknown_tool_{name}"})


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_onboarding_snapshot",
                "description": (
                    "Read the current signup record: what is already saved, what is still "
                    "missing, subscription plans, and payment status. Call this whenever you "
                    "need accurate database state (always prefer over guessing)."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_onboarding_fields",
                "description": (
                    "Persist one or more signup fields. Only include fields the user has "
                    "clearly given. plan_key: lite, standard, or premium. "
                    "billing_interval: monthly or yearly."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "full_name": {"type": "string"},
                        "business_name": {"type": "string"},
                        "business_address": {"type": "string"},
                        "email": {"type": "string"},
                        "plan_key": {
                            "type": "string",
                            "description": "lite, standard, or premium",
                        },
                        "billing_interval": {
                            "type": "string",
                            "description": "monthly or yearly",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_paystack_checkout",
                "description": (
                    "Create the tenant, user link, and Paystack payment link. Required: full "
                    "name, business name, address, email, plan, and billing interval must "
                    "already be saved (use save_onboarding_fields first, or snapshot). "
                    "Only call when the user is ready to pay. Returns the real Paystack URL—"
                    "never invent a payment link."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_platform_knowledge",
                "description": (
                    "Search FAQs, policies, and how Whatcommerce works. Use for questions "
                    "about billing, the product, or support—not for user-specific data."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "reset_onboarding",
                "description": "Clear this chat's saved signup and start over (e.g. user asks to restart).",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]
