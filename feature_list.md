# Whatcommerce — Feature list

A checklist derived from the product plan. Use it for backlog ordering and acceptance; adjust wording when scope changes.

## Billing & plans

- [ ] **No free plan** — all access is subscription-based.
- [ ] **Lite** — 50 products, 2 users, ₦5,000 / month.
- [ ] **Standard** — 100 products, 3 users, ₦10,000 / month.
- [ ] **Premium** — 500 products, 5 users, ₦20,000 / month.
- [ ] **Yearly and monthly** billing options.
- [ ] **Paystack payment links** for checkout after plan selection.
- [ ] **Paystack webhooks** as the system of record for **payment success/failure** and account activation.
- [ ] **Inactive → active** transition only after verified payment (user “I paid” is UX, not truth).
- [ ] **Subscription expiry** stored and shown (super admin + internal enforcement).

## Public web (Next.js)

- [ ] **Landing page** (clear value prop, trust, CTA).
- [ ] **Get started** → opens WhatsApp chat to the **configured** bot number (wa.me or equivalent).
- [ ] Optional: UTM or campaign params preserved on redirect (if desired later).

## Super admin (web)

- [ ] **Authentication** for super admin only (mechanism TBD: credentials, 2FA later).
- [ ] **User list** — all platform users/tenants with **plan** and **expiry date**.
- [ ] **Subscription plan management** — create/edit **plan** definitions (limits, NGN prices, monthly/yearly where applicable).
- [ ] **WhatsApp bot setup** — define which number/session is used for the landing page CTA.
- [ ] **WhatsApp reconnect** — flow to restore `whatsapp-web.js` session (e.g. QR) when disconnected.
- [ ] **Knowledge base & FAQ** — CRUD and ingestion path for **RAG** (chunking, update/delete, optional preview).

## WhatsApp bridge (`whatsapp-web.js`)

- [ ] **Inbound** messages (text; **voice notes** in scope for product vision).
- [ ] **Outbound** replies, payment links, and later **documents** (PDF, XLSX exports).
- [ ] **Session lifecycle** — connect, disconnect, reconnect; surface status to super admin.
- [ ] **Stable phone identity** mapping to platform user/tenant (normalisation, deduplication).

## Onboarding (new user via bot)

- [ ] Detect **new vs existing** user by phone (or equivalent).
- [ ] **Welcome** and optional Q&A before commitment.
- [ ] Collect **name**, **business name**, **business address**, **email**.
- [ ] **Plan** + **duration** (monthly/yearly).
- [ ] Create **user/tenant in inactive** state with chosen plan.
- [ ] **Generate and send** Paystack link on WhatsApp.
- [ ] If user claims payment: **“verifying”** message while awaiting webhook.
- [ ] On webhook **success/failure**: explicit WhatsApp message on **what happens next**.

## Active tenant — commerce / ERP (WhatsApp + agent)

- [ ] **Products** — list, create, edit, delete (enforce per-plan product caps).
- [ ] **Orders** — add, view, edit (and related workflows as you define).
- [ ] **Users** — up to per-plan user limit (invite/add/remove as designed).
- [ ] **Business consultation** context — agent with tools + (optional) search.
- [ ] **Export business information** to **PDF** and **XLSX** and deliver via WhatsApp.
- [ ] **Voice notes** — receive and process per agent design (STT and policies).

## Agents & intelligence

- [ ] **OpenAI Agent SDK** for primary agent(s) (e.g. store manager, onboarding sub-flows).
- [ ] **Serper** (or equivalent) for **Google search** when enabled.
- [ ] **RAG** over super-admin **knowledge base and FAQ** for accurate answers.
- [ ] **Tooling** to FastAPI: CRUD, subscription checks, exports, search—aligned with product limits.

## Backend (FastAPI + `uv`)

- [ ] REST (or RPC-style) **tenant-scoped** APIs for commerce entities.
- [ ] **Admin** APIs for super admin features.
- [ ] **Internal** APIs for WhatsApp worker (message events, send, session flags).
- [ ] **Webhook** endpoint for Paystack (signing, idempotency, mapping to tenant/subscription).
- [ ] **Enforcement** of plan limits (products, users) on mutating operations.

## Non-functional (initial)

- [ ] **Secrets** — API keys, Paystack, OpenAI, Serper, DB, session encryption for WhatsApp creds.
- [ ] **Logging** — webhooks, payments, bridge errors, agent failures.
- [ ] **Basic health** — API up, DB reachable, bridge connected (or degraded state visible to admin).

---

*Derived from `Planning.md`.*
