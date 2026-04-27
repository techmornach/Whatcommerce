import re
from urllib.parse import urlparse

_MD_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def _normalize_url(url: str, public_api_base_url: str | None) -> str:
    u = (url or "").strip()
    if not u:
        return u
    base = (public_api_base_url or "").strip().rstrip("/")
    # Repair malformed model output like: https://files/products/...
    # This should map to the API file route: <PUBLIC_API_BASE_URL>/files/products/...
    if u.startswith(("http://", "https://")):
        try:
            p = urlparse(u)
            if p.netloc == "files" and p.path.startswith("/products/") and base:
                return f"{base}/files{p.path}"
        except Exception:
            pass
    if u.startswith(("http://", "https://")):
        return u
    if u.startswith("/"):
        if base:
            return f"{base}{u}"
    return u


def _unwrap_markdown_images(s: str, public_api_base_url: str | None) -> str:
    def repl(m):
        label = (m.group(1) or "").strip()
        url = _normalize_url((m.group(2) or "").strip(), public_api_base_url)
        if not url:
            return m.group(0)
        if label:
            return f"{label}: {url}"
        return url

    return _MD_IMAGE.sub(repl, s)


def _unwrap_markdown_links(s: str, public_api_base_url: str | None) -> str:
    def repl(m):
        label = (m.group(1) or "").strip()
        url = _normalize_url((m.group(2) or "").strip(), public_api_base_url)
        if not url:
            return m.group(0)
        if label:
            return f"{label}: {url}"
        return url

    return _MD_LINK.sub(repl, s)


def normalize_whatsapp_markup(text: str, *, public_api_base_url: str | None = None) -> str:
    s = (text or "").replace("\r\n", "\n")
    s = _unwrap_markdown_images(s, public_api_base_url)
    s = _unwrap_markdown_links(s, public_api_base_url)
    while "**" in s:
        s2 = _MD_BOLD.sub(r"*\1*", s)
        if s2 == s:
            break
        s = s2
    return s
