"""Public URLs for post-payment WhatsApp linking."""

from app.core.config import get_settings
from app.models.tenant import Tenant


def wa_link_public_url(tenant: Tenant) -> str | None:
    if tenant.wa_link_token is None:
        return None
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/v1/public/wa-link/{tenant.wa_link_token}"
