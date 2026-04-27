# Whatcommerce Setup Guide

This guide is for a fresh clone and covers local development end-to-end:

- API (FastAPI + Alembic + Postgres)
- Web (Next.js)
- WhatsApp bridge (optional but recommended for full flow)

## 1) Prerequisites

Install these first:

- Docker Desktop (or Docker Engine + Compose)
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (Python package/project manager)
- Node.js 20+ and npm
- Git

Quick checks:

```bash
docker --version
docker compose version
python3 --version
uv --version
node --version
npm --version
```

## 2) Clone and enter the repo

```bash
git clone <YOUR_REPO_URL> whatcommerce
cd whatcommerce
```

## 3) Start Postgres

This project includes a Postgres container in `docker-compose.yml`.
It exposes host port `5433` (not `5432`) to avoid local conflicts.

```bash
docker compose up -d
docker compose ps
```

Wait until `db` is healthy.

## 4) Configure and run the API

Open a terminal in `api/`:

```bash
cd api
cp .env.example .env
```

Review/edit `api/.env` as needed. For local defaults, these are the key values:

- `DATABASE_URL=postgresql+psycopg://whatcommerce:whatcommerce@127.0.0.1:5433/whatcommerce`
- `CORS_ORIGINS=http://localhost:3000`
- `BOOTSTRAP_ADMIN=1`
- `ADMIN_BOOTSTRAP_EMAIL=admin@example.com`
- `ADMIN_BOOTSTRAP_PASSWORD=ChangeMe1!`
- `INTERNAL_API_KEY=dev-internal-key-change-in-production`

Install dependencies and run migrations:

```bash
uv sync
uv run alembic upgrade heads
```

Start the API:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sanity checks:

- Health: `http://127.0.0.1:8000/health`
- Docs: `http://127.0.0.1:8000/docs`

## 5) Configure and run the Web app

Open a new terminal in `web/`:

```bash
cd web
npm install
```

Create local env file:

```bash
cat > .env.local <<'EOF'
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
EOF
```

Start web dev server:

```bash
npm run dev
```

Open:

- Landing page: `http://localhost:3000`
- Admin login: `http://localhost:3000/admin/login`

If `BOOTSTRAP_ADMIN=1`, default admin credentials come from `api/.env`.

## 6) Configure and run WhatsApp bridge (optional)

This powers QR pairing + inbound/outbound WhatsApp traffic.

Open another terminal in `whatsapp/whatcommerce/`:

```bash
cd whatsapp/whatcommerce
cp .env.example .env
npm install
npm start
```

Required values in `whatsapp/whatcommerce/.env`:

- `WHATCOMMERCE_API_BASE=http://127.0.0.1:8000`
- `INTERNAL_API_KEY=dev-internal-key-change-in-production` (must match `api/.env`)
- `DISPATCH_PORT=3001`

If you want API-triggered outbound messages (for events like payment activation), set this in `api/.env`:

```env
WHATSAPP_BRIDGE_DISPATCH_URL=http://127.0.0.1:3001/dispatch
```

Then restart the API process.

## 7) Optional integrations

- **OpenAI store manager**: set `OPENAI_API_KEY` in `api/.env`
- **Paystack**:
  - set `PAYSTACK_SECRET_KEY` in `api/.env`
  - webhook path is `/api/paystack/webhook`
  - for local testing, expose API via a tunnel (for example ngrok)

## 8) Common development commands

From `api/`:

```bash
uv run alembic current
uv run alembic upgrade heads
uv run pytest
```

From `web/`:

```bash
npm run lint
npm run build
```

From root:

```bash
docker compose logs -f db
docker compose down
```

## 9) Troubleshooting

- **Web cannot reach API / CORS errors**
  - Verify `NEXT_PUBLIC_API_URL` in `web/.env.local`
  - Verify `CORS_ORIGINS` in `api/.env` includes `http://localhost:3000`
  - Restart API after editing env vars

- **Alembic migration issues**
  - Ensure DB container is healthy
  - Use `uv run alembic upgrade heads` (not `head`)

- **Admin login fails**
  - Confirm `BOOTSTRAP_ADMIN=1` and bootstrap credentials in `api/.env`
  - Restart API so startup bootstrap runs

- **WhatsApp stuck at startup**
  - Ensure `INTERNAL_API_KEY` matches in API and bridge env files
  - Delete local bridge session dir and restart bridge:
    `rm -rf whatsapp/whatcommerce/.wwebjs`

- **Hidden runtime artifacts appearing in git**
  - This repo ignores `.wwebjs` and hidden runtime folders under `whatsapp/`
  - If already tracked previously, untrack once:
    `git rm -r --cached whatsapp/whatcommerce/.wwebjs`

## 10) Recommended terminal layout

Run these in parallel:

- Terminal 1: `docker compose up -d` (root)
- Terminal 2: API (`cd api && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)
- Terminal 3: Web (`cd web && npm run dev`)
- Terminal 4: Bridge (`cd whatsapp/whatcommerce && npm start`)

That is the full local stack.
