"""
WhatsApp text quirks (LLMs often emit Markdown instead):
- Bold: *one* pair of asterisks; **double** often shows stray stars.
- Links: [label](url) is NOT supported—use plain https://... (auto-linkified).
See https://faq.whatsapp.com/539178204879377
"""

import re

_MD_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
# Markdown [text](https://...) — WhatsApp displays this literally; unwrap to plain URL.
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
    """Fix common Markdown so it matches what WhatsApp actually renders."""
    s = (text or "").replace("\r\n", "\n")
    s = _unwrap_markdown_links(s)
    while "**" in s:
        s2 = _MD_BOLD.sub(r"*\1*", s)
        if s2 == s:
            break
        s = s2
    return s
