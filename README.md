

## 🚀 Live Demo

* 🎥 **Video Walkthrough:**
  https://youtu.be/ODy3kcZvczk

* 🌐 **Live Application:**
  https://whatcommerce.play.jaraflytech.com/

---

## 🔐 Admin Access

* **Admin Panel:**
  https://whatcommerce.play.jaraflytech.com/admin

* **Credentials:**

  * **Username:** `admin@example.com`
  * **Password:** `ChangeMe1!`

---

# Whatcommerce

WhatsApp-first commerce for small vendors: **FastAPI** backend, **Next.js** marketing + super admin, **whatsapp-web.js** bridge, **Paystack** billing (onboarding + webhook activation).

## Quick start

1. **PostgreSQL** (Docker; host port **5433** so it does not clash with a local Postgres on 5432):

   ```bash
   docker compose up -d
   ```

2. **API** (from `api/`):

   ```bash
   cp .env.example .env
   uv sync
   uv run alembic upgrade heads
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   On startup, **Lite / Standard / Premium** plans and default landing WhatsApp settings are seeded. With `BOOTSTRAP_ADMIN=1`, a super admin is created (see `.env`).

   For **subscribers with an active plan**, the WhatsApp bot uses OpenAI for the *store manager* (products, orders). Set **`OPENAI_API_KEY`** in `api/.env`.

3. **Web** (from `web/`):

   ```bash
   echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
   npm install
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000). Super admin: [http://localhost:3000/admin/login](http://localhost:3000/admin/login) (default credentials in `api/.env` when bootstrap is enabled).

4. **WhatsApp bridge** (optional, from `whatsapp/whatcommerce/`):

   ```bash
   cp .env.example .env
   npm install
   npm start
   ```

   Scan the QR code; inbound messages are POSTed to `POST /api/internal/inbound-messages` with `X-Internal-Key`.  
   Set `WHATSAPP_BRIDGE_DISPATCH_URL=http://127.0.0.1:3001/dispatch` in `api/.env` (and `DISPATCH_PORT=3001` in the bridge) so the API can notify users after **Paystack** confirms payment (`POST /api/paystack/webhook`).

5. **Paystack**: set `PAYSTACK_SECRET_KEY` in `api/.env`, register the webhook URL `https://<your-host>/api/paystack/webhook` in the Paystack dashboard (use a tunnel such as ngrok for local dev).

## Project layout

| Path | Purpose |
|------|---------|
| `api/` | FastAPI, SQLAlchemy, Alembic, Paystack webhooks, admin + public JSON |
| `web/` | Next.js — landing + super admin dashboard |
| `whatsapp/whatcommerce/` | Long-lived Node process using `whatsapp-web.js` |

## Docs

- [SETUP.md](SETUP.md) — full local setup guide for fresh clones
- [deployment.md](deployment.md) — infrastructure + CI/CD deployment runbook
- [Planning.md](Planning.md) — product notes
- [architecture.md](architecture.md) — application architecture and runtime flows
- [deploy_architecture.md](deploy_architecture.md) — AWS deployment architecture (VPC, subnets, ALB, ASGs, RDS, CloudFront)
- [feature_list.md](feature_list.md) — checklist
