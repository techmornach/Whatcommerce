import base64
import io
import logging
import re
from typing import Any

from openai import OpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)

CHAT_LIKE = frozenset({"chat", "e2e_notification", "notification", "ciphertext"})
VOICE_TYPES = frozenset({"ptt", "audio", "voice", "in"})
IMAGE_TYPES = frozenset({"image", "sticker"})


def _decode_media_b64(
    media_base64: str, *, max_bytes: int
) -> tuple[bytes | None, str | None]:
    s = (media_base64 or "").strip()
    if not s:
        return None, "No media data."
    try:
        raw = base64.b64decode(s, validate=True)
    except Exception as e:  # noqa: BLE001
        logger.debug("b64 decode: %s", e)
        return None, "Invalid media data."
    if len(raw) > max_bytes:
        return None, f"File is too large (max {max_bytes // 1_048_576} MB from WhatsApp)."
    return raw, None


def _transcribe_audio(
    client: OpenAI, raw: bytes, mimetype: str, *, model: str
) -> str:
    ext = "ogg"
    m = re.search(r"audio/([a-z0-9]+)", (mimetype or "").lower() or "audio/ogg")
    if m and m.group(1) in ("ogg", "mpeg", "mp3", "mp4", "wav", "webm", "m4a", "x-m4a"):
        ext = m.group(1) if m.group(1) != "mpeg" else "mp3"
    filename = f"inbound.{ext}"
    bio = io.BytesIO(raw)
    bio.name = filename
    tr = client.audio.transcriptions.create(model=model, file=bio, response_format="text")
    if isinstance(tr, str):
        return (tr or "").strip()
    t = getattr(tr, "text", None)
    return (str(t) or "").strip() if t is not None else ""


def _describe_image(
    client: OpenAI,
    raw: bytes,
    mimetype: str,
    model: str,
) -> str:
    b64s = base64.b64encode(raw).decode("ascii")
    mt = mimetype or "image/jpeg"
    if not mt.startswith("image/"):
        mt = "image/jpeg"
    url = f"data:{mt};base64,{b64s}"
    r = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this WhatsApp image in detail: visible text, main subjects, "
                            "and anything relevant to a small-business shop assistant (products, "
                            "prices, errors on screen). If you cannot see clearly, say so briefly."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": url, "detail": "low"}},
                ],
            }
        ],
        max_tokens=800,
    )
    choice = r.choices[0] if r.choices else None
    msg = choice.message if choice else None
    c = (msg.content or "").strip() if msg else ""
    return c or "(empty description)"


def _is_audio_mimetype(m: str | None) -> bool:
    return bool(m and m.startswith("audio/"))


def _is_image_mimetype(m: str | None) -> bool:
    return bool(m and m.startswith("image/"))


def _is_video_mimetype(m: str | None) -> bool:
    return bool(m and m.startswith("video/"))


def normalize_inbound(
    settings: Settings,
    *,
    body: str,
    message_type: str | None,
    media_mimetype: str | None,
    media_base64: str | None,
) -> tuple[str, str, dict[str, Any], bytes | None]:
    """
    Return (canonical_text, kind, event_metadata, image_raw_bytes or None).
    `kind` is one of: text, voice, image, other.
    For successfully decoded inbound images, `image_raw_bytes` is set (for server-side save).
    """
    body = (body or "").strip()
    mtype = (message_type or "chat").lower().strip() or "chat"
    has_media = bool((media_base64 or "").strip())
    max_b = int(settings.inbound_media_max_bytes)

    # ——— Text only ———
    if not has_media:
        if mtype in CHAT_LIKE or mtype == "chat":
            return body, "text", {"mtype": mtype}, None
        if mtype in VOICE_TYPES:
            if body:
                meta = {"note": "transcript_unavailable", "mtype": mtype}
                return f"[Voice] {body}", "voice", meta, None
            return "", "voice", {"error": "no_media", "mtype": mtype}, None
        if mtype in IMAGE_TYPES and body:
            return (
                f"[Image — caption: {body}]\n(The image file was not received; caption only.)",
                "image",
                {"caption_only": True, "mtype": mtype},
                None,
            )
        if mtype in ("video", "document", "ptv"):
            msg = (
                "We do not process *video or documents* in chat yet. "
                "Please send *text*, a *photo*, or a *voice* note."
            )
            return msg, "other", {"unsupported_mtype": mtype, "router_short_circuit": True}, None
        if mtype in ("location", "vcard", "call_log", "revoked", "ciphertext", "e2e_notification"):
            if body:
                return body, "text", {"mtype": mtype}, None
            placeholder = f"[{mtype} message; content not available to the server]"
            return placeholder, "other", {"mtype": mtype}, None
        if body:
            return body, "text", {"mtype": mtype}, None
        return "", "text", {"empty": True, "mtype": mtype}, None

    # ——— With media (base64) ———
    raw, err = _decode_media_b64(media_base64 or "", max_bytes=max_b)
    if err:
        meta = {
            "error": "size_or_b64",
            "mtype": mtype,
            "router_short_circuit": True,
        }
        return err, "other", meta, None

    key = (settings.openai_api_key or "").strip()
    if not key:
        return (
            "The server cannot read images or voice until *OPENAI_API_KEY* is set.",
            "other",
            {"error": "no_openai_key", "router_short_circuit": True},
            None,
        )
    client = OpenAI(api_key=key)

    treat_as_image = mtype in IMAGE_TYPES or _is_image_mimetype(media_mimetype)
    treat_as_audio = mtype in VOICE_TYPES or _is_audio_mimetype(media_mimetype)

    if _is_video_mimetype(media_mimetype) and not treat_as_image:
        return (
            "We do not process *video* in chat yet. Please send a *photo* or *text*.",
            "other",
            {
                "unsupported_mime": media_mimetype,
                "mtype": mtype,
                "router_short_circuit": True,
            },
            None,
        )

    if treat_as_audio and not treat_as_image:
        try:
            t = _transcribe_audio(
                client, raw, media_mimetype or "audio/ogg", model=settings.openai_transcribe_model
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("transcription: %s", e)
            t = ""
        if not t:
            return (
                "I could not understand that audio. Please try again or type your message.",
                "voice",
                {"error": "transcription_empty", "mtype": mtype, "mimetype": media_mimetype},
                None,
            )
        return f'[Voice] "{t}"', "voice", {"mimetype": media_mimetype, "mtype": mtype}, None

    if treat_as_image:
        try:
            desc = _describe_image(
                client, raw, media_mimetype or "image/jpeg", model=settings.openai_vision_model
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("vision: %s", e)
            return (
                "I could not read that image. Please try a smaller photo or type your request.",
                "image",
                {"error": "vision_failed", "mtype": mtype},
                raw,
            )
        cap = f"Caption: {body}\n\n" if body else ""
        return f"[Image]\n{cap}Description: {desc}", "image", {
            "mimetype": media_mimetype,
            "mtype": mtype,
        }, raw

    # media present but type unclear: sniff by mimetype
    if _is_video_mimetype(media_mimetype):
        return (
            "We do not process *video* in chat yet. Please send a *photo* or *text*.",
            "other",
            {
                "unsupported_mime": media_mimetype,
                "mtype": mtype,
                "router_short_circuit": True,
            },
            None,
        )

    msg = (
        f"This file type is not fully supported (type={mtype}). "
        "Please send *text*, a *photo*, or a *voice* note."
    )
    return msg, "other", {
        "mtype": mtype,
        "mimetype": media_mimetype,
        "router_short_circuit": True,
    }, None
