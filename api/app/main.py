import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    admin_auth,
    admin_knowledge,
    admin_ops,
    admin_plans,
    admin_settings,
    admin_tenants,
    health,
    internal,
    paystack_webhook,
    public,
)
from app.core.config import get_settings
from app.services.bootstrap import run_startup_bootstrap
from app.services.product_image_storage import URL_PREFIX, upload_root

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    try:
        upload_root(s).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logging.getLogger(__name__).warning("product upload dir: %s", e)
    run_startup_bootstrap()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    is_prod = settings.api_env.strip().lower() in {"prod", "production"}
    app = FastAPI(
        title="Whatcommerce API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(public.router)
    app.include_router(admin_auth.router)
    app.include_router(admin_tenants.router)
    app.include_router(admin_plans.router)
    app.include_router(admin_settings.router)
    app.include_router(admin_knowledge.router)
    app.include_router(admin_ops.router)
    app.include_router(internal.router)
    app.include_router(paystack_webhook.router)
    # Local product images: /files/products/{tenant_id}/{file}
    root = upload_root(settings)
    root.mkdir(parents=True, exist_ok=True)
    app.mount(URL_PREFIX, StaticFiles(directory=str(root)), name="product_uploads")
    return app


app = create_app()
