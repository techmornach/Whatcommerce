from fastapi import FastAPI

from app.config import settings
from app.routers import health, whatsapp

app = FastAPI(title="Whatcommerce API", version="0.1.0")

app.include_router(health.router)
app.include_router(whatsapp.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "whatcommerce-api", "default_tenant": settings.default_tenant_id}
