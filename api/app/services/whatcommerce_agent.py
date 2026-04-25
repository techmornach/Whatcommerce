"""OpenAI Agents SDK for Whatcommerce platform Q&A (Serper + FAQ tools)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from agents import Agent, Runner, RunContextWrapper, function_tool

from app.core.config import get_settings
from app.services.serper import serper_search

logger = logging.getLogger(__name__)

_MAX_OUT = 12_000


@dataclass
class WhatcommerceContext:
    """Injected into tools; FAQ text is snapshotted before the run."""

    knowledge_base_text: str


@function_tool
async def search_web(query: str) -> str:
    """Search the public web via Serper (Google). Use short, specific queries."""
    q = (query or "").strip()
    if len(q) < 2:
        return "Query too short."
    try:
        data = await serper_search(q, num=6)
        return json.dumps(data, default=str)[:_MAX_OUT]
    except RuntimeError as e:
        return f"Search unavailable: {e}"


@function_tool
async def get_platform_policy(ctx: RunContextWrapper[WhatcommerceContext]) -> str:
    """Return super-admin FAQ / policy text configured for this deployment (RAG-lite)."""
    t = ctx.context.knowledge_base_text.strip()
    return t if t else "(No FAQ or knowledge base text configured yet.)"


_WHATCOMMERCE_INSTRUCTIONS = """You are the Whatcommerce assistant for Nigerian small businesses.
Whatcommerce is WhatsApp-first commerce: vendors subscribe (Lite ₦5k, Standard ₦10k, Premium ₦20k / month),
pay via Paystack, then run catalog and orders from WhatsApp.

Rules:
- Be concise; users are on WhatsApp (short paragraphs).
- For signup, tell them to reply YES in this chat to start the guided subscription flow (do not pretend you can charge them).
- Use get_platform_policy for product/policy questions when relevant.
- Use search_web for fresh public facts (competitors, regulations, etc.) when needed.
- Never invent Paystack URLs or tenant IDs.
"""


def _chunk_reply(text: str, limit: int = 3500) -> list[str]:
    text = (text or "").strip()
    if not text:
        return ["(empty response)"]
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if size + len(p) + 2 > limit and buf:
            parts.append("\n\n".join(buf))
            buf = [p]
            size = len(p)
        else:
            buf.append(p)
            size += len(p) + 2
    if buf:
        parts.append("\n\n".join(buf))
    return parts if parts else [text[:limit]]


async def run_whatcommerce_agent(*, user_message: str, knowledge_base_text: str) -> list[str]:
    settings = get_settings()
    if not settings.openai_api_key:
        return ["AI assistant is not configured (set OPENAI_API_KEY)."]
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    agent = Agent[WhatcommerceContext](
        name="whatcommerce",
        instructions=_WHATCOMMERCE_INSTRUCTIONS,
        tools=[search_web, get_platform_policy],
        model=settings.openai_model,
    )
    ctx = WhatcommerceContext(knowledge_base_text=knowledge_base_text or "")
    try:
        result = await Runner.run(agent, input=user_message.strip(), context=ctx, max_turns=12)
    except Exception:
        logger.exception("whatcommerce agent run failed")
        return ["Sorry, the assistant hit an error. Please try again or reply YES to subscribe."]
    out = result.final_output
    if isinstance(out, str):
        return _chunk_reply(out)
    return _chunk_reply(str(out))
