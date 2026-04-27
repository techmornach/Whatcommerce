"""
Extract text from allowed knowledge-base uploads (PDF, Markdown, plain text).
Reject videos, images, and other formats with clear user-facing messages.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)

ALLOWED_TEXT_EXT = frozenset({".md", ".markdown", ".txt"})

_VIDEO_MSG = (
    "Whatcommerce can’t import video files for the knowledge base. "
    "Please upload a PDF or Markdown (.md) file, or paste text."
)
_IMAGE_MSG = (
    "Whatcommerce can’t import image files for the knowledge base. "
    "Please upload a PDF or Markdown (.md) file, or paste text."
)
_UNSUPPORTED_MSG = (
    "Whatcommerce can’t import this file type. "
    "Supported: PDF and Markdown (.md / .markdown), or plain text (.txt). "
    "Or paste your content in the form."
)
_BINARY_OFFICE_MSG = (
    "Whatcommerce can’t import Word/Excel/PowerPoint files. "
    "Export as PDF or save as Markdown / plain text; or paste content."
)

_OFFICE_EXT = frozenset({".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".rtf"})
_VIDEO_EXT = frozenset({".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".ogv"})
_AUDIO_EXT = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac"})
_IMAGE_EXT = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"})


def _pdf_magic(b: bytes) -> bool:
    return len(b) >= 4 and b[:4] == b"%PDF"


def _extract_pdf(raw: bytes) -> tuple[str | None, str | None]:
    try:
        reader = PdfReader(io.BytesIO(raw))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        text = "\n\n".join(parts).strip()
    except Exception as e:  # noqa: BLE001
        logger.info("pdf extract failed: %s", e)
        return (
            None,
            "Couldn’t read this PDF. It may be encrypted or not text-based. Try another file.",
        )
    if not text:
        return (
            None,
            "No text could be extracted from this PDF. Try a text-based PDF or paste content.",
        )
    return text, None


def _extract_utf8_text(raw: bytes) -> tuple[str | None, str | None]:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc).strip()
            if text:
                return text, None
        except UnicodeDecodeError:
            continue
    return None, "Couldn’t decode this file as text. Save as UTF-8 or use PDF."


def extract_knowledge_file_text(
    filename: str,
    raw: bytes,
    content_type: str | None,
) -> tuple[str | None, str | None]:
    """
    Return (text, error_message). `error_message` is user-facing; `text` is set only on success.
    """
    if not raw:
        return None, "The uploaded file is empty."

    ext = Path(filename or "upload").suffix.lower()
    ct = (content_type or "").lower().split(";")[0].strip()

    if ct.startswith("video/"):
        return None, _VIDEO_MSG
    if ct.startswith("image/"):
        return None, _IMAGE_MSG
    if ct.startswith("audio/"):
        return None, _UNSUPPORTED_MSG

    if ext in _VIDEO_EXT:
        return None, _VIDEO_MSG
    if ext in _IMAGE_EXT:
        return None, _IMAGE_MSG
    if ext in _AUDIO_EXT:
        return None, _UNSUPPORTED_MSG
    if ext in _OFFICE_EXT:
        return None, _BINARY_OFFICE_MSG

    # PDF
    if ext == ".pdf":
        if not _pdf_magic(raw):
            return None, _UNSUPPORTED_MSG
        return _extract_pdf(raw)

    # Markdown / plain text
    if ext in ALLOWED_TEXT_EXT:
        return _extract_utf8_text(raw)

    # Unknown extension: only accept if raw bytes are a PDF
    if ext and ext not in {".pdf", *ALLOWED_TEXT_EXT}:
        return None, _UNSUPPORTED_MSG

    # ext == "" (no suffix): try PDF then reject
    if not ext:
        if _pdf_magic(raw):
            return _extract_pdf(raw)
        return None, (
            "Please upload a file named with an extension, e.g. "
            "`.pdf`, `.md`, or `.txt`."
        )

    return None, _UNSUPPORTED_MSG


def title_from_upload(filename: str) -> str:
    stem = Path(filename or "article").stem.strip() or "Article"
    return stem[:512]
