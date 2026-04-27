# Whatcommerce Architecture

This document explains how the application works at runtime.

## High-level system

```mermaid
flowchart LR
  U[Customer / Admin Browser] -->|HTTPS| W[Next.js Web App]
  W -->|REST API| A[FastAPI API]
  WA[WhatsApp User] -->|Messages| B[WhatsApp Bridge]
  B -->|POST /api/internal/inbound-messages| A
  A -->|POST /dispatch| B
  A --> DB[(PostgreSQL)]
  A --> S3[(S3 Uploads)]
  A --> OAI[OpenAI APIs]
  P[Paystack] -->|Webhook| A
```

## Request and message flow

### 1) Public/admin web flow

```mermaid
sequenceDiagram
  participant Browser as Browser
  participant Web as Next.js Web
  participant API as FastAPI
  participant DB as PostgreSQL

  Browser->>Web: Load page (/ or /admin/*)
  Web->>API: Fetch public/admin data
  API->>DB: Query/update entities
  DB-->>API: Result
  API-->>Web: JSON response
  Web-->>Browser: Rendered UI
```

### 2) WhatsApp inbound -> AI/tools -> outbound

```mermaid
sequenceDiagram
  participant WA as WhatsApp User
  participant Bridge as whatsapp-web.js Bridge
  participant API as FastAPI
  participant DB as PostgreSQL
  participant LLM as OpenAI
  participant Store as Product/Order Services

  WA->>Bridge: Inbound message/media
  Bridge->>API: POST /api/internal/inbound-messages
  API->>DB: Load tenant + conversation history
  API->>Store: Resolve intents/tools (orders, products, onboarding)
  API->>LLM: Generate/guard/humanize response
  LLM-->>API: Assistant output
  API->>DB: Save conversation events
  API->>Bridge: POST /dispatch (outbound text)
  Bridge-->>WA: WhatsApp reply delivered
```

### 3) Billing activation flow

```mermaid
sequenceDiagram
  participant User as Merchant/User
  participant API as FastAPI
  participant Paystack as Paystack
  participant DB as PostgreSQL
  participant Bridge as WhatsApp Bridge

  User->>API: Start onboarding/checkout
  API-->>User: Paystack checkout URL
  Paystack->>API: POST /api/paystack/webhook
  API->>DB: Verify + activate tenant plan
  API->>Bridge: POST /dispatch activation message
  Bridge-->>User: WhatsApp activation confirmation
```

## Core backend modules

- `api/app/api/routes`: HTTP entry points (public, admin, internal, webhook, files)
- `api/app/services`: business logic (onboarding, bridge status, store manager, knowledge, payment)
- `api/app/models`: SQLAlchemy entities
- `api/alembic`: DB migrations
- `whatsapp/whatcommerce/index.mjs`: WhatsApp bridge runtime
- `web/src/app` + `web/src/components`: landing and admin UI

## Storage model

- Primary transactional data: PostgreSQL
- Product/media uploads: local in dev, S3 in deployed environments
- WhatsApp session runtime cache: bridge local `.wwebjs` (not committed)

## Security boundaries

- Admin APIs require JWT bearer auth
- Internal APIs require `X-Internal-Key`
- CORS controlled by `CORS_ORIGINS`
- Cloud resources and env secrets managed through IAM + Secrets Manager in deployed envs
