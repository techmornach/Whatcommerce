from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin_auth,
    admin_platform,
    admin_portal,
    health,
    internal,
    payments_internal,
    paystack_webhook,
    public,
    store_manager_internal,
    tenants_internal,
    whatcommerce_internal,
)
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.lifecycle import ensure_default_billing_plans, ensure_default_platform_settings
from app.services.admin_bootstrap import ensure_bootstrap_admin

# Loopback hostnames + any port (Next dev on 3001, IPv6 ::1, etc.)
_LOCAL_NEXT_CORS_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"


def _cors_allow_origins() -> list[str]:
    base = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:3000",
    ]
    extra = [o.strip() for o in get_settings().cors_allow_origins.split(",") if o.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for o in base + extra:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        await ensure_default_platform_settings(session)
    async with AsyncSessionLocal() as session:
        await ensure_default_billing_plans(session)
    async with AsyncSessionLocal() as session:
        await ensure_bootstrap_admin(session)
    yield


app = FastAPI(title="Whatcommerce API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_origin_regex=_LOCAL_NEXT_CORS_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(admin_auth.router)
app.include_router(admin_portal.router)
app.include_router(public.router)
app.include_router(paystack_webhook.router)
app.include_router(internal.router)
app.include_router(admin_platform.router)
app.include_router(tenants_internal.router)
app.include_router(payments_internal.router)
app.include_router(store_manager_internal.router)
app.include_router(whatcommerce_internal.router)
