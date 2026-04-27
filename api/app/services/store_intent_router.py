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
    "If both appear, prefer **analyst** when any evaluative or opinion-seeking part exists.\n\n"
    "If unsure, prefer **analyst** for how is, what you think, or feedback; else "
    "**operations**."
)

_ANALYST_QUICK = re.compile(
    r"(what do you think|your (?:honest )?opinion|constructive feedback|feedback on|"
    r"rate my|review my|critique|how('?s| is) my|thoughts on|advice on|"
    r"whole store|store brand|my brand|positioning|marketing ideas|"
    r"does (?:this|my|the) (?:product|store|brand)|improve my|"
    r"how can i (?:improve|better))",
    re.I,
)


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
