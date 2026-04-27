import json
import logging
import uuid

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.messages.whatsapp_guardrails import INPUT_GUARD_REFUSAL
from app.services.agent_input_guard import (
    evaluate_input_guard,
    format_transcript_for_guard,
)
from app.services.agent_response_pipeline import postprocess_assistant_reply
from app.services.conversation_store import load_openai_messages
from app.services.guard_reporting import report_guard_block
from app.services.store_context import StoreContext
from app.services.store_intent_router import build_store_analyst_system, classify_store_intent
from app.services.store_tools import execute_store_tool
from app.utils.whatsapp_text import normalize_whatsapp_markup

logger = logging.getLogger(__name__)

STORE_SYSTEM = """You are Whatcommerce, an AI store manager on WhatsApp for small businesses
in Nigeria.

You help the shop owner manage *products* and *orders*. Be concise, friendly, and clear.
Use *bold* for key terms where it helps. Currency is Nigerian Naira (₦). For *links*, use
plain *https://…* text only—do not use `[label](url)` Markdown; WhatsApp does not render it.
Never invent stock levels or product IDs—always use the tools to read or change the database.
If a tool returns an error, explain it and suggest a fix.

Common intents: list or add products, create an order from product IDs, check recent orders,
store summary. If the user only greets you, reply briefly and offer 2–3 things you can do.

When the owner sends a *product photo*, the message may include a *Catalog image URL* (hosted on
this server). Pass that exact URL in *add_product* or *update_product* as *image_urls* so the
product keeps the image. You can call *describe_product_image* on that URL (or a *product_id*
that already has images) to generate a *description* before saving.

For *general* Whatcommerce *policies, billing basics, and FAQs*, call *search_platform_knowledge*
(Admin-maintained). Never use it to invent *this store* product stock or order details—
those come only from the other tools."""


def _openai_tool_definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_store_summary",
                "description": (
                    "Get business name, plan limits, product and order counts, subscription end."
                ),
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_products",
                "description": (
                    "List products: id, name, selling price (price_ngn), optional cost_price_ngn, "
                    "stock, description snippet, image_urls."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_inactive": {
                            "type": "boolean",
                            "description": "Include inactive/archived products",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_product",
                "description": (
                    "Add a new product. price_ngn is the *selling* price. Respects plan limit."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Product name"},
                        "price_ngn": {
                            "type": "integer",
                            "description": "Selling price in NGN (integer)",
                        },
                        "cost_price_ngn": {
                            "type": "integer",
                            "description": "Optional cost of goods in NGN",
                        },
                        "stock": {
                            "type": "integer",
                            "description": "Units in stock (default 0)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional product description",
                        },
                        "image_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Optional URLs: https or /files/products/… from a catalog photo "
                                "in chat"
                            ),
                        },
                    },
                    "required": ["name", "price_ngn"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_product",
                "description": "Update an existing product by id (same tenant only).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "price_ngn": {
                            "type": "integer",
                            "description": "Selling price in NGN",
                        },
                        "cost_price_ngn": {
                            "type": "integer",
                            "description": "Optional; omit field to leave unchanged, null to clear",
                        },
                        "stock": {"type": "integer"},
                        "description": {"type": "string"},
                        "image_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "is_active": {
                            "type": "boolean",
                            "description": "False to hide from default listings",
                        },
                    },
                    "required": ["product_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_product",
                "description": "Permanently delete a product by id.",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_orders",
                "description": "List recent orders with lines and totals.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max orders (1–50, default 10)",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_order",
                "description": "Create order; deducts stock. Each line: product_id and quantity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "quantity": {"type": "integer", "minimum": 1},
                                },
                                "required": ["product_id", "quantity"],
                            },
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Optional end-customer name",
                        },
                        "customer_phone": {
                            "type": "string",
                            "description": "Optional end-customer phone",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional order notes",
                        },
                    },
                    "required": ["lines"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "describe_product_image",
                "description": (
                    "Short catalog *description* from a stored product image (vision). "
                    "Use image_url from chat, or product_id (first product image)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_url": {
                            "type": "string",
                            "description": "/files/products/... URL or full URL for this store",
                        },
                        "product_id": {
                            "type": "integer",
                            "description": "Optional; first product image_urls entry",
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_platform_knowledge",
                "description": (
                    "Search the platform knowledge base (FAQs, policies, how Whatcommerce works). "
                    "Use for generic questions, not for this shop's product stock or order rows."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to look up (natural language or keywords)",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
    ]


def _split_whatsapp(
    text: str, max_len: int = 4000, *, public_api_base_url: str | None = None
) -> list[str]:
    t = (text or "").strip()
    if not t:
        return ["…"]
    if len(t) <= max_len:
        return [normalize_whatsapp_markup(t, public_api_base_url=public_api_base_url)]
    chunks: list[str] = []
    rest = t
    while rest:
        if len(rest) <= max_len:
            chunks.append(
                normalize_whatsapp_markup(rest, public_api_base_url=public_api_base_url)
            )
            break
        cut = rest.rfind("\n\n", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        chunks.append(
            normalize_whatsapp_markup(
                rest[:cut].strip(), public_api_base_url=public_api_base_url
            )
        )
        rest = rest[cut:].strip()
    return [c for c in chunks if c]


def run_store_manager(db: Session, ctx: StoreContext) -> list[str]:
    settings = get_settings()
    public_api_base_url = (settings.public_api_base_url or "").strip() or None
    if not (settings.openai_api_key or "").strip():
        return [
            "The *store manager* is not available: set *OPENAI_API_KEY* on the API server. "
            "Your subscription is still active."
        ]

    hlimit = max(1, min(settings.conversation_history_max_events, 64))
    history = load_openai_messages(
        db, phone_e164=ctx.phone_e164, tenant_id=ctx.tenant_id, limit=hlimit
    )
    if not history:
        return _split_whatsapp(
            "Sorry, the conversation was empty. Please send a message again.",
            public_api_base_url=public_api_base_url,
        )

    ig = evaluate_input_guard(settings, history)
    if ig.blocked:
        max_ch = max(500, int(getattr(settings, "agent_input_guard_max_context_chars", 4000)))
        report_guard_block(
            db,
            kind="input",
            flow="store",
            phone_e164=ctx.phone_e164,
            latest_user_message=(history[-1].get("content") or "") if history else "",
            context_excerpt=format_transcript_for_guard(history, max_chars=min(max_ch, 3000)),
            category=ig.category,
            blocked_content_summary=(
                f"*Classifier JSON (excerpt):*\n{(ig.model_reply_excerpt or '')}"
            ),
        )
        return _split_whatsapp(
            INPUT_GUARD_REFUSAL, public_api_base_url=public_api_base_url
        )

    trace_id = uuid.uuid4().hex[:16]
    trace_user = f"wc-t{ctx.tenant_id}-{trace_id}"
    last_msg = (history[-1].get("content") or "").strip() if history else ""
    route = classify_store_intent(
        settings, last_user_message=last_msg, trace_user=trace_user
    )
    if route == "analyst":
        system = build_store_analyst_system(settings, ctx)
        model = (settings.openai_store_analyst_model or "").strip() or settings.openai_model
    else:
        system = (
            f"{STORE_SYSTEM}\n\n"
            f"You are working with *{ctx.business_name}* ({ctx.plan_name} plan, "
            f"max {ctx.max_products} products). The owner is *{ctx.user_display_name}*. "
            f"Address their latest message; keep prior turns in mind for context only."
        )
        model = settings.openai_model

    logger.info(
        "store_manager: tenant_id=%s intent=%s model=%s wc_trace_id=%s",
        ctx.tenant_id,
        route,
        model,
        trace_id,
    )

    client = OpenAI(api_key=settings.openai_api_key)
    max_rounds = max(1, min(settings.store_manager_max_tool_rounds, 12))
    tools = _openai_tool_definitions()

    messages: list[dict] = [{"role": "system", "content": system}, *history]

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            user=trace_user,
        )
        choice = response.choices[0] if response.choices else None
        if not choice:
            return _split_whatsapp(
                "I couldn’t generate a reply. Please try again.",
                public_api_base_url=public_api_base_url,
            )
        msg = choice.message

        if not msg.tool_calls:
            content = (msg.content or "").strip()
            if not content:
                return _split_whatsapp("Done.", public_api_base_url=public_api_base_url)
            content = postprocess_assistant_reply(
                content,
                settings=settings,
                db=db,
                history=history,
                phone_e164=ctx.phone_e164,
                flow="store",
            )
            return _split_whatsapp(content, public_api_base_url=public_api_base_url)

        asst: dict = {"role": "assistant", "content": msg.content}
        tcalls = list(msg.tool_calls)
        asst["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            }
            for tc in tcalls
        ]
        messages.append(asst)

        for tc in tcalls:
            name = tc.function.name
            raw_args = tc.function.arguments or "{}"
            try:
                result_str = execute_store_tool(db, ctx, name, raw_args)
            except Exception as e:
                logger.exception("store tool %s: %s", name, e)
                result_str = json.dumps(
                    {"ok": False, "error": f"server_error: {e!s}"}
                )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                }
            )

    return _split_whatsapp(
        "I hit the tool step limit. Ask something simpler, or try again in a moment.",
        public_api_base_url=public_api_base_url,
    )
