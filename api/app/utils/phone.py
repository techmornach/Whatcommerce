import re

_NON_DIGIT = re.compile(r"\D+")


def normalize_to_e164(phone: str, default_country: str = "234") -> str:
    s = (phone or "").strip()
    s = s.replace("whatsapp:", "")
    s = s.split("@", 1)[0]
    d = _NON_DIGIT.sub("", s)
    if not d:
        return s if s else ""
    if d.startswith("0") and len(d) in (10, 11) and not d.startswith("00"):
        d = default_country + d[1:]
    elif not d.startswith(default_country) and len(d) == 10 and d.startswith("0"):
        d = default_country + d[1:]
    if d and not s.startswith("+"):
        return f"+{d}"
    if s.startswith("+"):
        return f"+{d}" if d else s
    return s if s.startswith("+") else f"+{d}"


def wa_chat_id_to_phone_e164(wa_chat_id: str, default_country: str = "234") -> str:
    s = (wa_chat_id or "").strip()
    if "@" in s:
        user_part = s.split("@", 1)[0]
        d = _NON_DIGIT.sub("", user_part)
    else:
        d = _NON_DIGIT.sub("", s)
    if not d:
        return ""
    return normalize_to_e164(d, default_country=default_country)
