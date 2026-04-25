def normalize_phone_e164(raw: str) -> str:
    return "".join(c for c in (raw or "") if c.isdigit())
