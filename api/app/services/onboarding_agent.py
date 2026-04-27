import json
import logging

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.messages.whatsapp_guardrails import INPUT_GUARD_REFUSAL
from app.messages.whatsapp_onboarding import (
    EMPTY_REPLY,
    LLM_NO_CHOICE,
    NO_HISTORY,
    NO_OPENAI,
    SETUP_COMPLETE,
    TOOL_ROUND_LIMIT,
)
from app.models.enums import OnboardingState
from app.prompts.load_onboarding import get_onboarding_system_base
from app.services.agent_input_guard import (
    evaluate_input_guard,
    format_transcript_for_guard,
)
from app.services.agent_response_pipeline import postprocess_assistant_reply
from app.services.conversation_store import load_openai_messages
from app.services.guard_reporting import report_guard_block
from app.services.onboarding_tools import (
    build_snapshot,
    execute_onboarding_tool,
    get_or_create_onboarding_session,
    tool_definitions,
)
from app.utils.whatsapp_text import normalize_whatsapp_markup

logger = logging.getLogger(__name__)


def _split_whatsapp(text: str, max_len: int = 4000) -> list[str]:
    t = (text or "").strip()
    if not t:
        return [EMPTY_REPLY]
    if len(t) <= max_len:
        return [normalize_whatsapp_markup(t)]
    chunks: list[str] = []
    rest = t
    while rest:
        if len(rest) <= max_len:
            chunks.append(normalize_whatsapp_markup(rest))
            break
        cut = rest.rfind("\n\n", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        chunks.append(
            normalize_whatsapp_markup(rest[:cut].strip())
        )
        rest = rest[cut:].strip()
    return [c for c in chunks if c]


def run_onboarding_agent(
    db: Session, *, wa_chat_id: str, phone_e164: str
) -> list[str]:
    settings = get_settings()
    if not (settings.openai_api_key or "").strip():
        return [NO_OPENAI]

    session = get_or_create_onboarding_session(db, wa_chat_id, phone_e164)
    if session.state == OnboardingState.complete:
        return _split_whatsapp(SETUP_COMPLETE)

    hlimit = max(1, min(settings.conversation_history_max_events, 64))
    history = load_openai_messages(
        db, phone_e164=phone_e164, tenant_id=None, limit=hlimit
    )
    if not history:
        return _split_whatsapp(NO_HISTORY)

    ig = evaluate_input_guard(settings, history)
    if ig.blocked:
        max_ch = max(500, int(getattr(settings, "agent_input_guard_max_context_chars", 4000)))
        report_guard_block(
            db,
            kind="input",
            flow="onboarding",
            phone_e164=phone_e164,
            latest_user_message=(history[-1].get("content") or "") if history else "",
            context_excerpt=format_transcript_for_guard(history, max_chars=min(max_ch, 3000)),
            category=ig.category,
            blocked_content_summary=(
                f"*Classifier JSON (excerpt):*\n{(ig.model_reply_excerpt or '')}"
            ),
        )
        return _split_whatsapp(INPUT_GUARD_REFUSAL)

    try:
        snap = json.dumps(build_snapshot(db, session), default=str, indent=2)[:12_000]
    except Exception as e:
        logger.exception("onboarding snapshot: %s", e)
        snap = "{}"

    base = get_onboarding_system_base(settings)
    system = f"{base}\n\n---\n*Current signup state (from database):*\n```json\n{snap}\n```\n"
    system += (
        "You are in an *ongoing* WhatsApp thread—the messages after this system block "
        "are prior user/assistant turns (oldest to newest). Do not re-welcome the user on "
        "every reply; they already see the chat history. "
        "Address the *latest user message*; use the snapshot for saved fields, not for "
        "inventing names."
    )
    messages: list[dict] = [
        {"role": "system", "content": system},
        *history,
    ]
    max_rounds = max(1, min(getattr(settings, "store_manager_max_tool_rounds", 6), 12))
    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model
    tools = tool_definitions()
    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        choice = response.choices[0] if response.choices else None
        if not choice:
            return _split_whatsapp(LLM_NO_CHOICE)
        msg = choice.message
        if not msg.tool_calls:
            content = (msg.content or "").strip()
            if not content:
                return _split_whatsapp(EMPTY_REPLY)
            content = postprocess_assistant_reply(
                content,
                settings=settings,
                db=db,
                history=history,
                phone_e164=phone_e164,
                flow="onboarding",
            )
            return _split_whatsapp(content)
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
                result_str = execute_onboarding_tool(
                    db,
                    session=session,
                    name=name,
                    arguments=raw_args,
                )
            except Exception as e:
                logger.exception("onboarding tool %s: %s", name, e)
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
        db.refresh(session)
    return _split_whatsapp(TOOL_ROUND_LIMIT)
