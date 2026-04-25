# Conversation memory (Whatcommerce)

Short-lived project context for handoffs. Update when major behavior changes.

## 2026-04-24 — Platform outbound + dead letters + metrics

- **Owner order notifications** enqueue `worker_channel=whatcommerce`. The **whatcommerce** Node worker polls `POST /v1/internal/whatcommerce/outbound/claim` (no `TENANT_ID`), sends from the **platform** WhatsApp session, then `POST .../outbound/ack` or **`POST .../outbound/forgive`** if ack retries are exhausted (avoids duplicate sends after a successful `sendMessage`).
- **Store-manager worker** still polls `POST /v1/internal/store-manager/outbound/claim` with `tenant_id` for rows with `worker_channel=store_manager` (reserved for future business-line outbounds).
- **Retries / dead letter:** `attempt_count` increments on stale `sending` timeouts and on `POST .../report-fail` (e.g. `sendMessage` threw). After **`WHATSAPP_OUTBOUND_MAX_ATTEMPTS`** (default 5), the row becomes **`dead_letter`** with `failure_class` / `dead_letter_at`. Stale threshold: **`WHATSAPP_OUTBOUND_STALE_MINUTES`** (default 10).
- **Metrics:** `GET /v1/internal/whatcommerce/outbound/metrics?since_hours=24` (internal secret) returns counts by status, by `(worker_channel, status)`, recent dead letters, and config echo.
- **DB:** table **`whatsapp_outbound_messages`** (renamed from `store_manager_outbound_messages`); model **`WhatsappOutboundMessage`** in `api/app/models/whatsapp_outbound.py`; queue logic in **`api/app/services/outbound_queue.py`**.
- **Workers:** `whatsapp/shared/bridge.mjs` — both channels run outbound polling; env **`OUTBOUND_POLL_MS`**, **`OUTBOUND_ACK_RETRIES`**.

## 2026-04-24 — Earlier notes (still true)

- **Two WhatsApp surfaces:** `whatcommerce` (platform onboarding + Paystack + owner order pings) and `store_manager` (catalog, orders, owner confirm/reject). Each store-manager process sets `TENANT_ID` in `.env`.
- **Post-payment WA link:** `wa_link_token` / `wa_link_expires_at`; worker may send `WA_LINK_TOKEN` on `register-session` while the link is valid.
- **Owner-only gates:** `confirm_order` / `reject_order` require sender phone to match `tenants.onboarding_phone_e164` (digits-normalized).
- **Register-session duplicate checks** use PostgreSQL `regexp_replace(..., '[^0-9]', '', 'g')` for legacy phone formatting.

## Sensible next steps (not implemented)

- Ops UI for dead-letter replay / export.
- Prometheus-style counters instead of DB-only metrics.
