# Whatcommerce API

FastAPI backend for Whatcommerce. Run from this directory:

```bash
docker compose -f ../docker-compose.yml up -d
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
