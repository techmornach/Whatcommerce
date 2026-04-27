"""
Product image storage (local filesystem by default, optional S3 backend).
URLs are served under /files/products/{tenant_id}/{filename}.
"""

from __future__ import annotations

import base64
import logging
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from openai import OpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Paths under the upload root: {tenant_id}/{filename}
URL_PREFIX = "/files/products"

_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def upload_root(settings: Settings) -> Path:
    p = Path(settings.product_upload_dir)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


def _extension_for_mimetype(mimetype: str | None) -> str:
    m = (mimetype or "image/jpeg").lower().split(";")[0].strip()
    return _MIME_TO_EXT.get(m, "jpg")


def _mimetype_for_filename(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    if ext in {"jpg", "jpeg"}:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    if ext == "gif":
        return "image/gif"
    return "application/octet-stream"


def public_path_for_tenant_file(tenant_id: int, filename: str) -> str:
    return f"{URL_PREFIX}/{tenant_id}/{filename}"


def public_url_for_path(settings: Settings, path: str) -> str:
    """path starts with /files/products/..."""
    base = (settings.public_api_base_url or "").strip().rstrip("/")
    if not base:
        return path
    return f"{base}{path}"


def _s3_bucket(settings: Settings) -> str:
    return (settings.product_uploads_s3_bucket or "").strip()


def _is_s3_enabled(settings: Settings) -> bool:
    return bool(_s3_bucket(settings))


def _s3_client(settings: Settings):
    kwargs = {}
    if (settings.product_uploads_s3_region or "").strip():
        kwargs["region_name"] = settings.product_uploads_s3_region.strip()
    return boto3.client("s3", **kwargs)


def _s3_key(tenant_id: int, filename: str, *, prefix: str) -> str:
    pfx = (prefix or "").strip().strip("/")
    base = f"{tenant_id}/{filename}"
    return f"{pfx}/{base}" if pfx else base


def save_product_image(
    settings: Settings,
    *,
    tenant_id: int,
    raw: bytes,
    mimetype: str | None,
) -> str:
    """
    Write bytes to disk; return *path* for URLs (/files/products/...).
    """
    ext = _extension_for_mimetype(mimetype)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = public_path_for_tenant_file(tenant_id, name)
    if _is_s3_enabled(settings):
        key = _s3_key(tenant_id, name, prefix=settings.product_uploads_s3_prefix)
        try:
            _s3_client(settings).put_object(
                Bucket=_s3_bucket(settings),
                Key=key,
                Body=raw,
                ContentType=(mimetype or _mimetype_for_filename(name)),
            )
            return path
        except (BotoCoreError, ClientError) as e:
            raise OSError(f"s3 put_object failed: {e}") from e

    root = upload_root(settings)
    tdir = root / str(tenant_id)
    tdir.mkdir(parents=True, exist_ok=True)
    fpath = tdir / name
    fpath.write_bytes(raw)
    return path


def parse_product_image_path(url_or_path: str) -> tuple[int, str] | None:
    """
    Accept full URL or path like /files/products/3/abc.jpg -> (3, "abc.jpg").
    """
    s = (url_or_path or "").strip()
    if not s:
        return None
    path = urlparse(s).path if "://" in s else s
    if not path.startswith(f"{URL_PREFIX}/"):
        return None
    rest = path[len(f"{URL_PREFIX}/") :].lstrip("/")
    parts = rest.split("/")
    if len(parts) < 2:
        return None
    try:
        tid = int(parts[0])
    except ValueError:
        return None
    fname = parts[1]
    if not fname or ".." in fname or "/" in fname:
        return None
    if not re.match(r"^[a-f0-9]{32}\.\w{2,4}$", fname, re.I):
        return None
    return tid, fname


def resolve_tenant_image_file(settings: Settings, *, tenant_id: int, url_or_path: str) -> Path | None:
    parsed = parse_product_image_path(url_or_path)
    if parsed is None:
        return None
    tid, fname = parsed
    if tid != tenant_id:
        return None
    fp = upload_root(settings) / str(tid) / fname
    if not fp.is_file():
        return None
    return fp


def read_tenant_image_bytes(
    settings: Settings, *, tenant_id: int, url_or_path: str
) -> tuple[bytes, str] | None:
    parsed = parse_product_image_path(url_or_path)
    if parsed is None:
        return None
    tid, fname = parsed
    if tid != tenant_id:
        return None

    if _is_s3_enabled(settings):
        key = _s3_key(tid, fname, prefix=settings.product_uploads_s3_prefix)
        try:
            res = _s3_client(settings).get_object(Bucket=_s3_bucket(settings), Key=key)
            raw = res["Body"].read()
            mt = (res.get("ContentType") or _mimetype_for_filename(fname)).strip()
            return raw, mt or _mimetype_for_filename(fname)
        except ClientError:
            return None
        except BotoCoreError as e:
            logger.warning("s3 get_object failed: %s", e)
            return None

    fp = resolve_tenant_image_file(settings, tenant_id=tenant_id, url_or_path=url_or_path)
    if fp is None:
        return None
    return fp.read_bytes(), _mimetype_for_filename(fp.name)


def generate_catalog_description(
    client: OpenAI,
    raw: bytes,
    mimetype: str,
    *,
    model: str,
) -> str:
    """Short product blurb for a store catalog (WhatsApp-friendly)."""
    b64s = base64.b64encode(raw).decode("ascii")
    mt = mimetype or "image/jpeg"
    if not mt.startswith("image/"):
        mt = "image/jpeg"
    url = f"data:{mt};base64,{b64s}"
    r = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is a product photo for a small business in Nigeria selling on "
                            "WhatsApp. Write a *short* catalog description (2–4 sentences, plain "
                            "text). Mention what the product is, any visible key details, and tone "
                            "for shoppers. Do not invent a price. If the image is unclear, say so "
                            "briefly and describe what you can see."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": url, "detail": "low"}},
                ],
            }
        ],
        max_tokens=400,
    )
    choice = r.choices[0] if r.choices else None
    msg = choice.message if choice else None
    c = (msg.content or "").strip() if msg else ""
    return c or "(empty description)"
