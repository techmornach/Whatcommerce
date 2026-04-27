from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.config import get_settings
from app.services.product_image_storage import URL_PREFIX, read_tenant_image_bytes

router = APIRouter(tags=["files"])


@router.get(f"{URL_PREFIX}" + "/{tenant_id}/{filename}")
def get_product_image(tenant_id: int, filename: str) -> Response:
    settings = get_settings()
    loaded = read_tenant_image_bytes(
        settings, tenant_id=tenant_id, url_or_path=f"{URL_PREFIX}/{tenant_id}/{filename}"
    )
    if loaded is None:
        raise HTTPException(status_code=404, detail="Image not found")

    raw, mimetype = loaded
    return Response(
        content=raw,
        media_type=mimetype,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
