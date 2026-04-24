# Whatcommerce

## Vision

Across Africa, traditional ERP and inventory tooling is often heavy, expensive, and hard for small and medium businesses to operate day to day. **Whatcommerce** is a product-first platform that helps businesses manage stock, products, and orders while offering an **AI shop assistant** on **WhatsApp**—where their customers and staff already communicate.

The web dashboard is the control plane for configuration, reporting, and team management. WhatsApp is the conversational surface for staff workflows and customer self-service, backed by permissions, human approval where needed, and optional human handoff.

## Product pillars

1. **Inventory and commerce core** — Products, orders (sales), and basic ERP-style operations in one place.
2. **Role-based access** — Account owners create team members with granular permissions; the AI agent only exposes tools that match each user’s role.
3. **Company knowledge (RAG)** — Policies, returns, FAQs, and guidelines as PDFs or in-app rich text, embedded per account for grounded answers.
4. **WhatsApp-native AI** — OpenAI-powered agent with curated tools (CRUD, search, optional browser/research), distinct behaviour for **staff** vs **public customers**.

## Authentication and identity

- **Primary auth for the admin web app**: [Clerk](https://clerk.com) handles sign-in, sessions, and subscription gating (see Billing). Email and password (or Clerk-supported methods) with email verification, password reset, and **device-aware 2FA** when signing in from a new device.
- **WhatsApp linkage**: Staff users are tied to **verified WhatsApp numbers** configured by the account admin. The bot resolves the sender’s number to an internal user and loads that user’s permissions—not “WhatsApp as the only identity provider,” but WhatsApp as the **channel key** for bot access.

## Web dashboard (account owner and team)

After authentication, users can:

- Manage **products** and **orders/sales** (view, create, edit, delete according to role).
- **Connect WhatsApp** for the store by scanning a **QR code** produced by your hosted **[whatsapp-web.js](https://wwebjs.dev/)** session (WhatsApp Web–style pairing in Chromium). This is **not** the Meta WhatsApp Cloud API: you run the Web client and bridge events to the backend.
- **Invite sub-users** under the same billing account and assign roles, for example:

  | Area    | Capabilities                                      |
  |---------|---------------------------------------------------|
  | Products | View, create, edit, delete                      |
  | Sales / orders | View, create, edit, delete                |

Each invited user must have a **WhatsApp number** on file so the bot can recognise them.

- **Company documents**: Upload PDFs (policies, returns, shipping, brand voice) or maintain pages in an **in-app editor**. Content is chunked and indexed for **per-account RAG** so the agent answers with account-specific context.

## WhatsApp AI agent

- **Runtime**: AI agent built with the **OpenAI SDK** (tool calling, streaming where applicable).
- **Tooling (illustrative)**:
  - **Product / order / sales CRUD** — Scoped by tenant and by the messaging user’s permissions.
  - **Serper** (or similar) — Web search for fresh public information when allowed by policy.
  - **Playwright via MCP** — Optional automation or fetch flows where you explicitly allow it (rate limits, allowlists, and audit logs are strongly recommended).

### Staff messaging the bot

When a **configured team user** messages the bot, the agent receives a **permission-filtered tool set** only—no tool for an action the user cannot perform in the dashboard. They can execute tasks, query stock, draft messages, and consult using RAG over company documents.

### Unknown numbers (customers)

If the sender is **not** a registered team user, they are treated as a **customer**:

- **Product discovery**: Limited product fields (no cost or internal SKU exposure unless you choose otherwise).
- **Orders**: A customer can **initiate** an order; it is **not** committed until a team member with **create order** permission **confirms or rejects** via WhatsApp. Rejections include a reason the bot can relay to the customer.
- **Human handoff**: The bot can escalate to a human, sending them the thread context, a short summary, and a clear ask (“approve order,” “policy exception,” etc.).

## Technology stack

| Layer        | Choice |
|-------------|--------|
| API / business logic | **Python**, **FastAPI** |
| Admin UI   | **Next.js** |
| WhatsApp bridge | **Node.js**, **whatsapp-web.js** (Puppeteer / Chromium), talks to FastAPI over an internal API or queue — **no Meta Cloud API** |
| Cloud      | **AWS** |
| IaC        | **Terraform** |
| CI/CD      | **GitHub Actions** |

**Deployment goal**: Ephemeral or long-lived **dev**, **staging**, and **prod** environments from GitHub Actions—create and destroy non-prod stacks cleanly; **production** deploys to **`whatcommerce.ifedayo.dev`** on merge to the production branch (or tag policy you define in Actions).

## Billing and plans

Subscription-only: **no permanent free tier**. Every paid tier includes a **7-day trial** with **credit card required** upfront.

| Tier     | Products | Team users | PDF docs (500 words each) | Price / month (list → discounted) |
|----------|----------|------------|---------------------------|-------------------------------------|
| **Lite** | 30 max   | 2          | 1                         | $8 → **$5**                         |
| **Standard** | 100 max | 5      | 3                         | $15 → **$10**                       |
| **Premium** | 500 max | 10     | 10                        | $30 → **$20**                       |

> **Note:** Clerk excels at authentication and can orchestrate **billing** (often via **Stripe** under the hood). Finalise whether subscriptions live in Clerk Billing, Stripe Billing, or a hybrid; enforce limits (products, users, PDFs) in your API from the canonical subscription record.

## Super admin

A **super admin** (platform operator) can view accounts, **suspend** access, and **change or upgrade plans**—separate from normal tenant admins.

## Glossary

- **Order / sale** — Same domain concept; naming can be unified in the UI (“Orders”).
- **Tenant / account** — One paying organisation and its data boundary.
- **RAG** — Retrieval-augmented generation: retrieve relevant document chunks before the model answers.

## Related document

See **`architecture.md`** for system diagrams, AWS-oriented service breakdown, deployment strategy, and end-to-end user flows.
