"""
Post-process assistant text: optional output guard (safety), optional humanizer (tone).
Reads toggles from `platform_settings` via `platform_agent_flags`.
Fails open on guard errors; on humanizer errors returns the pre-humanizer text.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Literal

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.messages.whatsapp_guardrails import OUTPUT_GUARD_REPLACEMENT
from app.services.agent_input_guard import format_transcript_for_guard, parse_guard_json
from app.services.guard_reporting import report_guard_block
from app.services.platform_agent_flags import is_humanizer_enabled, is_output_guard_enabled

logger = logging.getLogger(__name__)

_BUNDLED_OUTPUT_GUARD = (
    Path(__file__).resolve().parent.parent / "prompts" / "agent_output_guard.md"
)
_BUNDLED_HUMANIZER = (
    Path(__file__).resolve().parent.parent / "prompts" / "agent_humanizer.md"
)


def _load_text(path: Path, fallback: str) -> str:
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError as e:
            logger.error("read %s: %s", path, e)
    return fallback


def _last_user_message(history: list[dict[str, str]]) -> str:
    for m in reversed(history):
        if m.get("role") == "user":
            return (m.get("content") or "").strip()
    return ""


def _output_guard_model(settings: Settings) -> str:
    return (settings.openai_output_guard_model or "").strip() or settings.openai_model


def _humanizer_model(settings: Settings) -> str:
    return (settings.openai_humanizer_model or "").strip() or settings.openai_model


def _run_output_guard(
    draft: str, settings: Settings
) -> tuple[str, bool, str | None, str | None]:
    """
    Returns (text, blocked, category, model_excerpt). If blocked, text is replacement string.
    """
    if not (settings.openai_api_key or "").strip():
        return draft, False, None, None
    system = _load_text(
        _BUNDLED_OUTPUT_GUARD,
        "Reply JSON only: {allow: true or false} for safe customer WhatsApp text.",
    )
    user = (
        "Message to review (this is what would be sent to the end user):\n\n"
        f"{draft[:12_000]}"
    )
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model=_output_guard_model(settings),
            temperature=0,
            max_tokens=120,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        ch = r.choices[0] if r.choices else None
        content = (ch.message.content if ch and ch.message else None) or ""
        excerpt = (content or "")[:800] or None
        data = parse_guard_json(content)
        if not isinstance(data, dict):
            logger.warning("output guard: bad JSON, allowing")
            return draft, False, None, None
        if data.get("allow") is True:
            return draft, False, None, None
        if data.get("allow") is False:
            cat = data.get("category", "")
            if cat is not None:
                cat = str(cat).strip() or None
            logger.info("output guard blocked: %s", cat)
            return OUTPUT_GUARD_REPLACEMENT, True, cat, excerpt
        return draft, False, None, None
    except Exception as e:
        logger.warning("output guard error (allowing): %s", e)
        return draft, False, None, None


def _run_humanizer(
    draft: str, settings: Settings, last_user: str
) -> str:
    if not (settings.openai_api_key or "").strip():
        return draft
    system = _load_text(
        _BUNDLED_HUMANIZER,
        "Rewrite the draft to be clear and warm for WhatsApp. Output the message only.",
    )
    user = (
        f"User's latest message (context, do not reply to it directly—only improve the draft):\n"
        f"{(last_user or '(none)')[:4_000]}\n\n"
        f"Draft reply to polish:\n{draft[:10_000]}"
    )
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model=_humanizer_model(settings),
            temperature=0.4,
            max_tokens=min(2_000, 400 + len(draft) // 2),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        ch = r.choices[0] if r.choices else None
        out = (ch.message.content if ch and ch.message else None) or ""
        out = re.sub(
            r"^\s*Here[’']s the (rewritten|updated|revised) message:?\s*",
            "",
            out,
            flags=re.I,
        )
        out = (out or "").strip()
        if not out:
            return draft
        if len(out) > 8_000:
            out = out[:8_000] + "…"
        return out
    except Exception as e:
        logger.warning("humanizer error (using original draft): %s", e)
        return draft


def postprocess_assistant_reply(
    draft: str,
    *,
    settings: Settings,
    db: Session,
    history: list[dict[str, str]],
    phone_e164: str | None = None,
    flow: Literal["onboarding", "store"] | None = None,
) -> str:
    """
    Apply output guard and optional humanizer. `draft` is the raw assistant string
    to send (before chunking for WhatsApp).
    """
    t = (draft or "").strip()
    if not t:
        return t
    original_draft = t

    if is_output_guard_enabled(db):
        t, blocked, out_cat, out_excerpt = _run_output_guard(t, settings)
        if blocked:
            if phone_e164 and flow:
                max_ch = max(
                    500, int(getattr(settings, "agent_input_guard_max_context_chars", 4000))
                )
                ctx = format_transcript_for_guard(history, max_chars=min(max_ch, 3000))
                report_guard_block(
                    db,
                    kind="output",
                    flow=flow,
                    phone_e164=phone_e164,
                    latest_user_message=_last_user_message(history),
                    context_excerpt=ctx,
                    category=out_cat,
                    blocked_content_summary=(
                        f"*Classifier response (excerpt):*\n{(out_excerpt or '')}\n\n"
                        f"*Blocked assistant draft (original):*\n{original_draft[:4000]}"
                    ),
                )
            return t
    if is_humanizer_enabled(db):
        t = _run_humanizer(t, settings, _last_user_message(history))
    return t
