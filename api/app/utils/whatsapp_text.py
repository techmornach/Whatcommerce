import os
import re

_MD_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(((?:https?://|/)[^)]+)\)")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(((?:https?://|/)[^)]+)\)")
_FILES_PATH = re.compile(r"(?<!https?://)(/files/products/\d+/[A-Za-z0-9]+\.[A-Za-z0-9]+)")


def _public_api_base_url() -> str:
    return (os.getenv("PUBLIC_API_BASE_URL") or "").strip().rstrip("/")


def _to_clickable_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("/"):
        base = _public_api_base_url()
        if base:
            return f"{base}{u}"
    return u


def _unwrap_markdown_images(s: str) -> str:
    def repl(m):
        alt = (m.group(1) or "").strip()
        raw = (m.group(2) or "").strip()
        url = _to_clickable_url(raw)
        if not url:
            return m.group(0)
        if alt:
            return f"{alt}: {url}"
        return url

    return _MD_IMAGE.sub(repl, s)


def _unwrap_markdown_links(s: str) -> str:
    def repl(m):
        label = (m.group(1) or "").strip()
        raw = (m.group(2) or "").strip()
        url = _to_clickable_url(raw)
        if not url:
            return m.group(0)
        if label:
            return f"{label}: {url}"
        return url

    return _MD_LINK.sub(repl, s)


def normalize_whatsapp_markup(text: str) -> str:
    s = (text or "").replace("\r\n", "\n")
    s = _unwrap_markdown_images(s)
    s = _unwrap_markdown_links(s)
    s = _FILES_PATH.sub(lambda m: _to_clickable_url(m.group(1)), s)
    while "**" in s:
        s2 = _MD_BOLD.sub(r"*\1*", s)
        if s2 == s:
            break
        s = s2
    return s
