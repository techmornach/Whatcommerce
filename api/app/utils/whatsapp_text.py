import re

_MD_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_MD_LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)")


def _unwrap_markdown_links(s: str) -> str:
    def repl(m):
        label = (m.group(1) or "").strip()
        url = (m.group(2) or "").strip()
        if not url:
            return m.group(0)
        if label:
            return f"{label}: {url}"
        return url

    return _MD_LINK.sub(repl, s)


def normalize_whatsapp_markup(text: str) -> str:
    s = (text or "").replace("\r\n", "\n")
    s = _unwrap_markdown_links(s)
    while "**" in s:
        s2 = _MD_BOLD.sub(r"*\1*", s)
        if s2 == s:
            break
        s = s2
    return s
