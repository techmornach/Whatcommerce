import html
import io
import json
from datetime import datetime, timezone
from uuid import UUID

import segno
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_PLATFORM_SETTINGS_ID
from app.db.session import get_db
from app.models.platform import PlatformSettings
from app.models.tenant import Tenant

router = APIRouter(prefix="/v1/public", tags=["public"])


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/config")
async def public_config(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == DEFAULT_PLATFORM_SETTINGS_ID))
    row = result.scalar_one_or_none()
    session_phone = row.whatcommerce_session_phone_e164 if row else None
    return {
        # Number logged into the platform whatcommerce worker (session-ready); sole source for public wa.me
        "whatcommerce_session_phone_e164": session_phone,
        "has_knowledge_base": bool(row and row.knowledge_base_text) if row else False,
        "whatcommerce_platform_connected": bool(
            row
            and row.whatcommerce_session_ready_at
            and row.whatcommerce_session_phone_e164
        )
        if row
        else False,
    }


@router.get("/wa-link/{token}", response_class=HTMLResponse)
async def wa_link_landing(token: str, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    """Post-payment page: instructions + QR payload for tenant/store-manager setup (MVP)."""
    try:
        tok = UUID(token)
    except ValueError:
        return HTMLResponse("<p>Invalid link.</p>", status_code=404)

    result = await db.execute(select(Tenant).where(Tenant.wa_link_token == tok))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return HTMLResponse("<p>Unknown link.</p>", status_code=404)

    now = datetime.now(timezone.utc)
    if tenant.wa_link_expires_at is None or _utc(tenant.wa_link_expires_at) < now:
        return HTMLResponse(
            "<p>This link has expired. Message the Whatcommerce bot again after payment if you need help.</p>",
            status_code=410,
        )

    payload = json.dumps({"v": 1, "tenant_id": str(tenant.id), "token": str(tok)}, separators=(",", ":"))
    qr = segno.make(payload, error="m")
    svg_buf = io.StringIO()
    qr.write_svg(svg_buf, scale=3)
    svg = svg_buf.getvalue()

    name = html.escape(tenant.business_name)
    tid = html.escape(str(tenant.id))
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Link store — Whatcommerce</title></head>
<body style="font-family:system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem;">
<h1>Link your business WhatsApp</h1>
<p><strong>Shop:</strong> {name}</p>
<p><strong>Tenant ID:</strong> <code>{tid}</code></p>
<ol>
<li>On the server (or laptop) that should host this shop&apos;s WhatsApp session, copy <code>whatsapp/store-manager/</code>.</li>
<li>Create <code>.env</code> with <code>TENANT_ID={tid}</code> (and API secrets).</li>
<li>Run <code>npm install</code> then <code>npm run start:store-manager</code>.</li>
<li>Scan the <strong>QR shown in the terminal</strong> with your <strong>business</strong> WhatsApp (not your personal onboarding number).</li>
</ol>
<p>The QR below encodes the same tenant id + token for a future mobile helper app — it is <em>not</em> the WhatsApp Web login QR.</p>
<div style="background:#fff;padding:1rem;border-radius:8px;display:inline-block;border:1px solid #ddd;">
{svg}
</div>
</body></html>"""
    )
