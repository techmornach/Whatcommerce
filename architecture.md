# Whatcommerce — Architecture

This document describes the high-level system design implied by the product plan. It is a starting point for implementation and can evolve as details are decided.

## Product in one line

A subscription-only WhatsApp-first commerce/ERP for small vendors: users onboard and operate (products, orders, exports, consultation) through conversational agents, with a small public web surface (landing + super admin) and Paystack for billing (NGN).

## Logical components

| Component | Role |
|-----------|------|
| **Web app (Next.js)** | Public landing with “Get started” → deep link to the configured WhatsApp number; super admin console for users/subscriptions/plans, bot connection, and knowledge/FAQ (RAG). |
| **WhatsApp bridge (Node, `whatsapp-web.js`)** | Maintains a WhatsApp Web–style session; receives/sends messages and media; must coordinate with the backend for identity, state, and agent runs. Unofficial client: account/session management and reconnection are first-class (see *Risks*). |
| **API (FastAPI, `uv`)** | REST (and webhooks): tenants/users, products, orders, billing state, admin auth, internal hooks from the WhatsApp worker and Paystack. Persistence and business rules. |
| **Agent layer (OpenAI Agent SDK + tools)** | “Store manager” and onboarding flows: tool calls into the API, optional Serper for web search, RAG over admin-managed knowledge. |
| **Payments (Paystack)** | Payment links and webhooks; **activation** of a tenant is driven by verified webhook results, not by user “I paid” alone. |
| **Data store** | Relational DB (choice TBD) for users/tenants, plans, subscriptions, products, orders, sessions, and outbound job metadata. Object storage optional later for exports. |

## Key flows (sequence)

### 1. Discovery → WhatsApp

1. Visitor opens landing page.  
2. Clicks “Get started”; opened URL targets the **super-admin-configured** WhatsApp number (and optional prefill).  
3. User messages the bot; bridge resolves **phone → platform user/tenant** (or “new”).

### 2. New user onboarding → inactive tenant → pay → active

1. If unknown: welcome + Q&A; when ready, collect **name, business name, business address, email**.  
2. **Plan** + **billing cycle** (monthly/yearly).  
3. Backend creates **user/tenant in inactive** state and generates a **Paystack payment link**; bridge sends it on WhatsApp.  
4. User may say they paid; bot responds with “verifying” while the **source of truth** is the webhook.  
5. **Paystack webhook** hits the API; on success, tenant becomes **active**, subscription window set; failure path communicated on WhatsApp.  
6. Post-activation: full commerce/ERP actions via the agent + API.

### 3. Super admin (web)

- Lists users, plan, **expiry**.  
- Edits **subscription plan definitions** (limits and prices as per product rules).  
- Configures which WhatsApp session / number powers the public “Get started” experience.  
- **Reconnect** WhatsApp when the `whatsapp-web.js` session drops (scan QR, etc.).  
- Manages **knowledge base + FAQ** ingested for RAG used by agents.

## Tech stack (as planned)

| Layer | Choice |
|-------|--------|
| Frontend | Next.js |
| Backend | FastAPI, package/runtime via `uv` |
| WhatsApp | `whatsapp-web.js` (unofficial) |
| Agents | OpenAI Agent SDK; Serper for search; RAG over admin content |
| Payments | Paystack (links + webhooks) |

## Suggested API boundaries (sketch)

- **Public/tenant-scoped** (or agent-internal): products CRUD, orders CRUD, tenant profile, usage within plan limits.  
- **Webhooks only**: Paystack (verify signature, idempotency, activate/deactivate or extend subscription).  
- **Internal** (bridge → API, secured): `POST` inbound message events, `GET`/`POST` for session status, send-message commands from server-side jobs if you split send/receive.  
- **Admin**: JWT/session for super admin; CRUD on plans, users, KB chunks, and WhatsApp config.

Exact route layout is an implementation detail; keep webhooks and internal bridge traffic **authenticated and rate-limited**.

## Data model highlights (conceptual)

- **BillingPlan** — name, max products, monthly/yearly price (NGN), active flag.  
- **Tenant** — business fields, plan reference, **status** (inactive/active), **subscription end** (expiry), Paystack customer/reference fields as needed.  
- **User** — link to tenant, role within tenant.  
- **Product / Order** — standard commerce shapes; enforce limits from plan.  
- **OnboardingSession** or **ConversationState** — optional explicit FSM for onboarding to survive restarts.  
- **KnowledgeDocument / Chunk** — for RAG, maintained from admin.  
- **WhatsApp / BridgeState** — session metadata, last connect, “landing” number mapping.

## Cross-cutting concerns

- **Idempotency**: Paystack webhooks and “create payment link” must tolerate duplicates.  
- **Phone identity**: normalise E.164; single tenant per “business” as product implies (clarify multi-location later if needed).  
- **Media**: voice notes and future exports (PDF, XLSX) need size limits, async generation, and delivery path on WhatsApp (document messages).  
- **Observability**: structured logs for webhook processing, agent tool calls, and bridge disconnects.

## Risks and constraints (WhatsApp Web)

- Not the official Cloud API: **ToS, stability, and multi-device** behavior differ; session loss is expected—admin **reconnect** is mandatory.  
- Keep the bridge on a **long-lived** process (or pool) with health checks; avoid splitting “auth” and “messaging” across nodes without a clear story for session stickiness.

## Future-friendly extensions (out of initial scope unless needed)

- Official WhatsApp Business API migration (different auth and ops model).  
- Additional payment providers or multi-currency.  
- Per-tenant API keys and web dashboard for sellers (still “WhatsApp-first”).

---

*Derived from `Planning.md`.*
