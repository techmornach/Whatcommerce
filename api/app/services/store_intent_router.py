from __future__ import annotations

import logging
import re
from pathlib import Path

from openai import OpenAI

from app.core.config import Settings
from app.services.agent_input_guard import parse_guard_json
from app.services.store_context import StoreContext

logger = logging.getLogger(__name__)

_INTENT_SYSTEM = (
    "You route the *last* user message for a WhatsApp shop assistant (Nigeria).\n\n"
    'Return JSON only: {"intent": "analyst"} or {"intent": "operations"}\n\n'
    "- **analyst** — Subjective help: opinions, what do you think, brand/store feedback, "
    "marketing, positioning, creative ideas, listing consistency, improving descriptions, "
    "retail advice, or reflection on their business.\n\n"
    "- **operations** — DB/bot actions or facts: add/edit/list products, orders, stock, "
    "prices, Paystack, subscription, how many products, pure hello with no advice, or "
    "step-by-step tasks with no evaluative ask.\n\n"
    "If both appear, prefer **operations** unless the user *explicitly* asks for evaluation, "
    "opinion, critique, ideas, or feedback.\n\n"
    "If the message includes product/order fields, IDs, prices, stock, or execution steps, choose "
    "**operations** even if tone is conversational.\n\n"
    "If unsure, default to **operations**."
)

_ANALYST_QUICK = re.compile(
    r"(what do you think|your (?:honest )?opinion|constructive feedback|feedback on|"
    r"rate my|review my|critique|how('?s| is) my|thoughts on|advice on|"
    r"whole store|store brand|my brand|positioning|marketing ideas|"
    r"does (?:this|my|the) (?:product|store|brand)|improve my|"
    r"how can i (?:improve|better))",
    re.I,
)

_OPERATIONS_QUICK = re.compile(
    r"(\badd(?:ing)?\b.*\bproduct\b|\bcreate\b.*\bproduct\b|\bnew product\b|"
    r"\bupdate\b.*\bproduct\b|\bedit\b.*\bproduct\b|\bdelete\b.*\bproduct\b|"
    r"\blist\b.*\bproduct\b|\bshow\b.*\bproduct\b|\bproduct details?\b|"
    r"\bprice(?:_ngn)?\b|\bcost(?:_price_ngn)?\b|\bstock\b|\bqty\b|\bquantity\b|"
    r"\bcreate\b.*\border\b|\bnew order\b|\blist\b.*\border\b|\bpaystack\b|\bsubscription\b)",
    re.I,
)


def _looks_structured_operations_payload(text: str) -> bool:
    """
    Detect WhatsApp-style field payloads, e.g.:
      name: AirPods
      price: 50000
      stock: 10
    """
    t = (text or "").strip().lower()
    if not t:
        return False
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    fields = ("name", "price", "price_ngn", "cost", "cost_price_ngn", "stock", "qty", "quantity")
    field_hits = sum(1 for ln in lines if any(ln.startswith(f"{k}:") for k in fields))
    return field_hits >= 2


def classify_store_intent(
    settings: Settings,
    *,
    last_user_message: str,
    trace_user: str,
) -> str:
    text = (last_user_message or "").strip()
    if not text:
        return "operations"

    if _ANALYST_QUICK.search(text):
        logger.debug("store intent: analyst (quick pattern)")
        return "analyst"

    if _OPERATIONS_QUICK.search(text) or _looks_structured_operations_payload(text):
        logger.debug("store intent: operations (quick pattern/payload)")
        return "operations"

    if not (settings.openai_api_key or "").strip():
        return "operations"

    model = (settings.openai_store_intent_model or "").strip() or settings.openai_model
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=80,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user", "content": f"Last user message:\n{text[:4000]}"},
            ],
            user=trace_user,
        )
        ch = r.choices[0] if r.choices else None
        raw = (ch.message.content if ch and ch.message else None) or ""
        data = parse_guard_json(raw)
        if isinstance(data, dict) and data.get("intent") == "analyst":
            logger.info("store intent: analyst (classifier)")
            return "analyst"
        if isinstance(data, dict) and data.get("intent") == "operations":
            logger.info("store intent: operations (classifier)")
            return "operations"
    except Exception as e:
        logger.warning("store intent classifier failed (defaulting operations): %s", e)

    return "operations"


def build_store_analyst_system(settings: Settings, ctx: StoreContext) -> str:
    override = (getattr(settings, "store_analyst_prompt_path", None) or "").strip()
    bundled = Path(__file__).resolve().parent.parent / "prompts" / "store_analyst.md"
    body: str
    if override:
        p = Path(override)
        if p.is_file():
            try:
                body = p.read_text(encoding="utf-8").strip()
            except OSError as e:
                logger.error("read store_analyst_prompt_path: %s", e)
                body = ""
        else:
            body = ""
    else:
        body = ""
    if not body and bundled.is_file():
        try:
            body = bundled.read_text(encoding="utf-8").strip()
        except OSError as e:
            logger.error("read store_analyst.md: %s", e)
            body = ""
    if not body:
        body = (
            "You are a helpful store analyst for small businesses. Give constructive feedback "
            "on brand and products using tools when needed."
        )
    return (
        f"{body}\n\n---\n"
        f"You are working with *{ctx.business_name}* ({ctx.plan_name} plan, "
        f"max {ctx.max_products} products). The owner is *{ctx.user_display_name}*.\n"
        "Address their latest message; use tools to ground advice in this store’s data when "
        "helpful."
    )
