"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  adminFetch,
  adminRequest,
  adminUpload,
  AUTH_TOKEN_KEY,
  getApiBaseUrl,
} from "@/lib/api";
import { useRouter } from "next/navigation";
import { WhatsAppQr } from "@/components/WhatsAppQr";

type Tenant = {
  id: number;
  business_name: string;
  contact_email: string;
  plan_key: string;
  plan_name: string;
  status: string;
  subscription_ends_at: string | null;
  owner_phone_e164: string | null;
  owner_name: string | null;
  product_count: number;
  order_count: number;
  last_message_at: string | null;
};

type Plan = {
  id: number;
  key: string;
  name: string;
  max_products: number;
  price_monthly_ngn: number;
  price_yearly_ngn: number;
  display_order: number;
  is_active: boolean;
};

type WhatsAppSettings = {
  link_state: string;
  connected_whatsapp_e164: string | null;
  bridge_status: string | null;
  bridge_message: string | null;
  bridge_updated_at: string | null;
  qr_data: string | null;
  landing_message_prefill: string;
};

type AgentPipelineSettings = {
  agent_output_guard_enabled: boolean;
  agent_humanizer_enabled: boolean;
  guard_report_whatsapp_e164: string;
};

type KbListItem = {
  id: number;
  title: string;
  is_published: boolean;
  body_preview: string;
  created_at: string;
  updated_at: string;
};

type KbDoc = {
  id: number;
  title: string;
  is_published: boolean;
  body: string;
  body_preview: string;
  created_at: string;
  updated_at: string;
};

type AdminSection =
  | "overview"
  | "whatsapp"
  | "agent"
  | "knowledge"
  | "plans"
  | "tenants";

function PlanEditForm({
  plan,
  token,
  onSaved,
}: {
  plan: Plan;
  token: string;
  onSaved: () => void | Promise<void>;
}) {
  const [name, setName] = useState(plan.name);
  const [maxP, setMaxP] = useState(plan.max_products);
  const [pm, setPm] = useState(plan.price_monthly_ngn);
  const [py, setPy] = useState(plan.price_yearly_ngn);
  const [order, setOrder] = useState(plan.display_order);
  const [active, setActive] = useState(plan.is_active);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    setName(plan.name);
    setMaxP(plan.max_products);
    setPm(plan.price_monthly_ngn);
    setPy(plan.price_yearly_ngn);
    setOrder(plan.display_order);
    setActive(plan.is_active);
  }, [plan]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await adminRequest<Plan>(`/api/admin/billing-plans/${plan.id}`, token, {
        method: "PUT",
        body: JSON.stringify({
          name,
          max_products: maxP,
          price_monthly_ngn: pm,
          price_yearly_ngn: py,
          display_order: order,
          is_active: active,
        }),
      });
      setMsg("Saved");
      await onSaved();
    } catch (x) {
      setMsg(x instanceof Error ? x.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="border border-zinc-800/80 rounded-lg p-4">
      <p className="text-xs text-zinc-500 mb-2">
        key: <code className="text-zinc-400">{plan.key}</code>
      </p>
      <form onSubmit={save} className="grid sm:grid-cols-2 gap-3 text-xs">
        <label className="sm:col-span-2">
          <span className="text-zinc-500">Name</span>
          <input
            className="w-full mt-0.5 rounded bg-zinc-900 border border-zinc-800 px-2 py-1.5"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <label>
          <span className="text-zinc-500">Max products</span>
          <input
            type="number"
            className="w-full mt-0.5 rounded bg-zinc-900 border border-zinc-800 px-2 py-1.5"
            value={maxP}
            onChange={(e) => setMaxP(parseInt(e.target.value, 10) || 0)}
            min={0}
          />
        </label>
        <label>
          <span className="text-zinc-500">Price monthly (₦)</span>
          <input
            type="number"
            className="w-full mt-0.5 rounded bg-zinc-900 border border-zinc-800 px-2 py-1.5"
            value={pm}
            onChange={(e) => setPm(parseInt(e.target.value, 10) || 0)}
            min={0}
          />
        </label>
        <label>
          <span className="text-zinc-500">Price yearly (₦)</span>
          <input
            type="number"
            className="w-full mt-0.5 rounded bg-zinc-900 border border-zinc-800 px-2 py-1.5"
            value={py}
            onChange={(e) => setPy(parseInt(e.target.value, 10) || 0)}
            min={0}
          />
        </label>
        <label>
          <span className="text-zinc-500">Display order</span>
          <input
            type="number"
            className="w-full mt-0.5 rounded bg-zinc-900 border border-zinc-800 px-2 py-1.5"
            value={order}
            onChange={(e) => setOrder(parseInt(e.target.value, 10) || 0)}
          />
        </label>
        <label className="flex items-end gap-2 pb-1">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />
          <span className="text-zinc-500">Active (shown in onboarding)</span>
        </label>
        <div className="sm:col-span-2 flex items-center gap-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-zinc-100 text-zinc-950 text-xs font-medium px-3 py-1.5 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save plan"}
          </button>
          {msg && (
            <span
              className={msg === "Saved" ? "text-zinc-300" : "text-zinc-400"}
            >
              {msg}
            </span>
          )}
        </div>
      </form>
    </li>
  );
}

function bridgeBadgeClass(s: string) {
  switch (s) {
    case "ready":
      return "bg-white/15 text-white";
    case "qr":
      return "bg-white/10 text-zinc-200";
    case "error":
      return "bg-white/10 text-zinc-300";
    case "init":
      return "bg-white/5 text-zinc-300";
    default:
      return "bg-zinc-500/20 text-zinc-400";
  }
}

export function DashboardClient({ section = "overview" }: { section?: AdminSection }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [tenants, setTenants] = useState<Tenant[] | null>(null);
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [wa, setWa] = useState<WhatsAppSettings | null>(null);
  const [agentPipeline, setAgentPipeline] = useState<AgentPipelineSettings | null>(
    null,
  );
  const [kb, setKb] = useState<KbListItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tenantQuery, setTenantQuery] = useState("");

  const load = useCallback(async (t: string, options?: { tenantQ?: string }) => {
    setErr(null);
    const tq = (options?.tenantQ !== undefined ? options.tenantQ : tenantQuery).trim();
    const tenantPath = tq
      ? `/api/admin/tenants?q=${encodeURIComponent(tq)}`
      : "/api/admin/tenants";
    const [a, b, c, ap, k] = await Promise.all([
      adminFetch<Tenant[]>(tenantPath, t),
      adminFetch<Plan[]>("/api/admin/billing-plans", t),
      adminFetch<WhatsAppSettings>("/api/admin/settings/whatsapp", t),
      adminFetch<AgentPipelineSettings>("/api/admin/settings/agent-pipeline", t),
      adminFetch<KbListItem[]>("/api/admin/knowledge/documents", t),
    ]);
    setTenants(a);
    setPlans(b);
    setWa(c);
    setAgentPipeline(ap);
    setKb(k);
  }, [tenantQuery]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const t = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!t) {
      router.replace("/admin/login");
      return;
    }
    setToken(t);
    load(t, { tenantQ: "" }).catch((e) => {
      if (String(e).includes("unauthorized") || e instanceof Error) {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        router.replace("/admin/login");
      } else {
        setErr(e instanceof Error ? e.message : "Failed to load");
      }
    });
  }, [load, router]);

  useEffect(() => {
    if (!token) return;
    const id = setInterval(() => {
      adminFetch<WhatsAppSettings>("/api/admin/settings/whatsapp", token)
        .then(setWa)
        .catch(() => {});
    }, 4000);
    return () => clearInterval(id);
  }, [token]);

  function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    router.push("/admin/login");
  }

  const activeTenants = tenants?.filter((t) => t.status === "active").length ?? 0;
  const totalProducts = tenants?.reduce((acc, t) => acc + t.product_count, 0) ?? 0;
  const totalOrders = tenants?.reduce((acc, t) => acc + t.order_count, 0) ?? 0;
  const panelClass = "rounded-2xl border border-white/10 bg-white/[0.03] p-5";
  const nav = [
    { key: "overview", label: "Overview", href: "/admin/overview" },
    { key: "whatsapp", label: "WhatsApp", href: "/admin/whatsapp" },
    { key: "agent", label: "Agent settings", href: "/admin/agent" },
    { key: "knowledge", label: "Knowledge base", href: "/admin/knowledge" },
    { key: "plans", label: "Billing plans", href: "/admin/plans" },
    { key: "tenants", label: "Tenants", href: "/admin/tenants" },
  ] as const;

  return (
    <div className="dark min-h-screen bg-black text-zinc-100">
      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 md:px-6 md:py-8">
        <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-64 flex-col rounded-2xl border border-white/10 bg-white/[0.02] p-4 md:flex">
          <div className="mb-6 border-b border-white/10 pb-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">
              Whatcommerce
            </p>
            <p className="mt-2 text-sm text-zinc-500">Admin console</p>
          </div>
          <nav className="space-y-1">
            {nav.map((item) => {
              const active = section === item.key;
              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className={`block rounded-lg px-3 py-2 text-sm transition ${
                    active
                      ? "bg-white text-black"
                      : "text-zinc-300 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            onClick={logout}
            className="mt-auto rounded-lg border border-white/15 px-3 py-2 text-left text-sm text-zinc-300 hover:bg-white/10 hover:text-white"
          >
            Sign out
          </button>
        </aside>

        <main className="w-full">
          <div className="mb-6 flex items-center justify-between gap-4 md:hidden">
            <p className="text-sm font-medium text-zinc-300">Admin console</p>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-sm text-zinc-200"
            >
              Sign out
            </button>
          </div>

          <div className="mb-6 overflow-x-auto md:hidden">
            <div className="flex gap-2">
              {nav.map((item) => {
                const active = section === item.key;
                return (
                  <Link
                    key={item.key}
                    href={item.href}
                    className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm ${
                      active
                        ? "bg-white text-black"
                        : "border border-white/15 text-zinc-300"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="mb-7">
            <h1 className="text-2xl font-semibold text-white">Admin dashboard</h1>
            <p className="mt-1 text-sm text-zinc-400">
              Manage WhatsApp, plans, knowledge, and tenant activity from one place.
            </p>
          </div>

          {err && <p className="mb-4 text-sm text-zinc-300">{err}</p>}

          {section === "overview" && (
            <>
              <section className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs text-zinc-400">Tenants</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{tenants?.length ?? "—"}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs text-zinc-400">Active subscriptions</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{activeTenants}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs text-zinc-400">Products tracked</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{totalProducts}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs text-zinc-400">Orders tracked</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{totalOrders}</p>
                </div>
              </section>

              <section className={`${panelClass} mb-8`}>
                <h2 className="mb-2 text-lg font-medium text-white">System overview</h2>
                <p className="text-sm text-zinc-400">
                  API endpoint: <code className="text-zinc-200">{getApiBaseUrl()}</code>
                </p>
                <p className="mt-2 text-sm text-zinc-400">
                  Use the menu to jump between WhatsApp setup, agent controls, knowledge,
                  pricing, and tenants.
                </p>
              </section>
            </>
          )}

          {section === "whatsapp" && (
            <section className={`${panelClass} mb-8`}>
              <h2 className="mb-2 text-lg font-medium text-white">WhatsApp bot &amp; public landing</h2>
              <p className="mb-4 text-sm text-zinc-400">
                After QR pairing, the public site automatically uses the connected WhatsApp
                number. You do not need to type a number here.
              </p>
              {wa && token ? (
                <WhatsAppLinkPanel
                  data={wa}
                  token={token}
                  onSaved={() => load(token, { tenantQ: tenantQuery })}
                />
              ) : (
                <p className="text-sm text-zinc-400">Loading…</p>
              )}
            </section>
          )}

          {section === "agent" && (
            <section className={`${panelClass} mb-8`}>
              <h2 className="mb-2 text-lg font-medium text-white">WhatsApp agent: safety &amp; tone</h2>
              <p className="mb-4 max-w-2xl text-sm text-zinc-400">
                Control how outgoing replies are checked and polished. You can block unsafe
                messages and optionally smooth tone before send. Configure models in{" "}
                <code className="text-zinc-200">OPENAI_OUTPUT_GUARD_MODEL</code> and{" "}
                <code className="text-zinc-200">OPENAI_HUMANIZER_MODEL</code>.
              </p>
              {token && agentPipeline ? (
                <AgentPipelinePanel
                  token={token}
                  data={agentPipeline}
                  onSaved={() => load(token, { tenantQ: tenantQuery })}
                />
              ) : (
                <p className="text-sm text-zinc-400">Loading…</p>
              )}
            </section>
          )}

          {section === "knowledge" && (
            <section className={`${panelClass} mb-8`}>
              <h2 className="mb-4 text-lg font-medium text-white">Knowledge base (RAG)</h2>
              {token && kb ? (
                <KnowledgeSection
                  token={token}
                  items={kb}
                  onChange={() => load(token, { tenantQ: tenantQuery })}
                />
              ) : (
                <p className="text-sm text-zinc-400">Loading…</p>
              )}
            </section>
          )}

          {section === "plans" && (
            <section className={`${panelClass} mb-8`}>
              <h2 className="mb-4 text-lg font-medium text-white">Billing plans</h2>
              {plans == null || !token ? (
                <p className="text-sm text-zinc-400">Loading…</p>
              ) : (
                <ul className="space-y-6 text-sm">
                  {plans.map((p) => (
                    <PlanEditForm
                      key={p.id}
                      plan={p}
                      token={token}
                      onSaved={() => load(token, { tenantQ: tenantQuery })}
                    />
                  ))}
                </ul>
              )}
            </section>
          )}

          {section === "tenants" && (
            <section className={panelClass}>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-medium text-white">Tenants & activity</h2>
                <p className="text-xs text-zinc-400">
                  API: <code>{getApiBaseUrl()}</code>
                </p>
              </div>
              {token && (
                <div className="mb-4 flex flex-wrap gap-2">
                  <input
                    type="search"
                    placeholder="Search business, email, phone, owner name, or id…"
                    className="w-full min-w-[200px] flex-1 rounded-lg border border-white/15 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-white/40"
                    value={tenantQuery}
                    onChange={(e) => setTenantQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && token) {
                        e.preventDefault();
                        load(token, { tenantQ: tenantQuery });
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black"
                    onClick={() => token && load(token, { tenantQ: tenantQuery })}
                  >
                    Search
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-white/15 px-4 py-2 text-sm text-zinc-200"
                    onClick={() => {
                      setTenantQuery("");
                      if (token) load(token, { tenantQ: "" });
                    }}
                  >
                    Clear
                  </button>
                </div>
              )}
              {tenants == null ? (
                <p className="text-sm text-zinc-400">Loading…</p>
              ) : tenants.length === 0 ? (
                <p className="text-sm text-zinc-400">
                  {tenantQuery.trim()
                    ? "No tenants match that search."
                    : "No tenants yet. New signups will appear here."}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-zinc-400">
                        <th className="py-2 pr-3">Business</th>
                        <th className="py-2 pr-3">Plan</th>
                        <th className="py-2 pr-3">Status</th>
                        <th className="py-2 pr-3">Products</th>
                        <th className="py-2 pr-3">Orders</th>
                        <th className="py-2 pr-3">Last WA msg</th>
                        <th className="py-2">Sub. ends</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tenants.map((t) => (
                        <tr key={t.id} className="border-b border-white/5">
                          <td className="py-2 pr-3 align-top">
                            {t.business_name}
                            <div className="text-xs text-zinc-500">{t.contact_email}</div>
                            {t.owner_phone_e164 && (
                              <div className="text-xs text-zinc-500">{t.owner_phone_e164}</div>
                            )}
                          </td>
                          <td className="py-2 pr-3 align-top">{t.plan_name}</td>
                          <td className="py-2 pr-3 align-top">{t.status}</td>
                          <td className="py-2 pr-3 tabular-nums align-top">{t.product_count}</td>
                          <td className="py-2 pr-3 tabular-nums align-top">{t.order_count}</td>
                          <td className="max-w-[140px] py-2 pr-3 align-top text-xs text-zinc-400">
                            {t.last_message_at
                              ? new Date(t.last_message_at).toLocaleString()
                              : "—"}
                          </td>
                          <td className="py-2 align-top text-xs text-zinc-400">
                            {t.subscription_ends_at
                              ? new Date(t.subscription_ends_at).toLocaleString()
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function KnowledgeSection({
  token,
  items,
  onChange,
}: {
  token: string;
  items: KbListItem[];
  onChange: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<KbDoc | "new" | null>(null);
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);

  async function startEdit(id: number) {
    setFormErr(null);
    setBusy(true);
    try {
      const d = await adminRequest<KbDoc>(`/api/admin/knowledge/documents/${id}`, token, {
        method: "GET",
      });
      setEditing(d);
    } catch (e) {
      setFormErr(e instanceof Error ? e.message : "Load failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {formErr && <p className="text-sm text-zinc-300">{formErr}</p>}
      {editing !== null && (
        <KbForm
          token={token}
          initial={editing}
          onClose={() => {
            setEditing(null);
            setFormErr(null);
          }}
          onSaved={async () => {
            setEditing(null);
            await onChange();
          }}
          onError={setFormErr}
        />
      )}
      <div className="flex justify-between items-center">
        <p className="text-sm text-zinc-500 max-w-lg">
          Published documents are indexed for assistant search. You can paste text or upload
          PDF, Markdown (.md), or .txt files.
        </p>
        <button
          type="button"
          onClick={() => {
            setFormErr(null);
            setEditing("new");
          }}
          className="shrink-0 text-sm rounded-md bg-zinc-100 text-zinc-950 font-medium px-3 py-1.5"
        >
          New article
        </button>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-zinc-500">No articles yet.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {items.map((d) => (
            <li
              key={d.id}
              className="flex flex-wrap items-start justify-between gap-2 border border-zinc-800 rounded-md p-3"
            >
              <div>
                <div className="font-medium">
                  {d.title}{" "}
                  {d.is_published ? (
                    <span className="text-xs text-zinc-300">(published)</span>
                  ) : (
                    <span className="text-xs text-zinc-500">(draft)</span>
                  )}
                </div>
                <div className="text-zinc-500 text-xs mt-1">{d.body_preview}</div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => startEdit(d.id)}
                  disabled={busy}
                  className="text-xs text-zinc-300 hover:underline"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    if (!confirm("Delete this article?")) return;
                    setBusy(true);
                    try {
                      await adminRequest(`/api/admin/knowledge/documents/${d.id}`, token, {
                        method: "DELETE",
                      });
                      await onChange();
                    } catch (e) {
                      setFormErr(e instanceof Error ? e.message : "Delete failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                  disabled={busy}
                  className="text-xs text-zinc-400 hover:underline"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function KbForm({
  token,
  initial,
  onClose,
  onSaved,
  onError,
}: {
  token: string;
  initial: "new" | KbDoc;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onError: (m: string | null) => void;
}) {
  const isNew = initial === "new";
  const [title, setTitle] = useState(isNew ? "" : initial.title);
  const [body, setBody] = useState(isNew ? "" : initial.body);
  const [isPublished, setIsPublished] = useState(
    isNew ? false : initial.is_published
  );
  const [importFile, setImportFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    onError(null);
    try {
      if (isNew && importFile) {
        const fd = new FormData();
        fd.append("file", importFile);
        fd.append("title", title.trim() || importFile.name);
        fd.append("is_published", isPublished ? "true" : "false");
        await adminUpload<KbDoc>("/api/admin/knowledge/documents/upload", token, fd);
      } else if (isNew) {
        await adminRequest<KbDoc>("/api/admin/knowledge/documents", token, {
          method: "POST",
          body: JSON.stringify({ title, body, is_published: isPublished }),
        });
      } else {
        await adminRequest<KbDoc>(`/api/admin/knowledge/documents/${initial.id}`, token, {
          method: "PUT",
          body: JSON.stringify({ title, body, is_published: isPublished }),
        });
      }
      await onSaved();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-lg border border-white/10 bg-zinc-900/40 p-4 space-y-3"
    >
      <div className="flex justify-between items-center">
        <h3 className="font-medium text-sm">
          {isNew ? "New knowledge article" : "Edit article"}
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-zinc-500 hover:text-zinc-300"
        >
          Close
        </button>
      </div>
      <div>
        <label className="text-xs text-zinc-500">Title</label>
        <input
          className="w-full mt-1 rounded-md bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required={!isNew || !importFile}
        />
      </div>
      {isNew && (
        <div>
          <label className="text-xs text-zinc-500">
            Import file (optional) — PDF, Markdown (.md), or plain text (.txt)
          </label>
          <input
            type="file"
            accept=".pdf,.md,.markdown,.txt,application/pdf,text/markdown,text/plain"
            className="w-full mt-1 text-sm text-zinc-300 file:mr-3 file:rounded file:border-0 file:bg-zinc-800 file:px-2 file:py-1"
            onChange={(e) => {
              const f = e.target.files?.[0];
              setImportFile(f ?? null);
            }}
          />
          {importFile && (
            <p className="mt-1 text-xs text-zinc-400">
              Saving will create this article from the uploaded file. The body field is ignored
              until you remove the file.
            </p>
          )}
        </div>
      )}
      <div>
        <label className="text-xs text-zinc-500">Body (plain text / markdown for your own use)</label>
        <textarea
          className="w-full mt-1 rounded-md bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm min-h-[160px] font-mono"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          disabled={isNew && !!importFile}
        />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isPublished}
          onChange={(e) => setIsPublished(e.target.checked)}
        />
        Published (available to assistant search)
      </label>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-zinc-100 text-zinc-950 text-sm font-medium px-4 py-2 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

function AgentPipelinePanel({
  token,
  data,
  onSaved,
}: {
  token: string;
  data: AgentPipelineSettings;
  onSaved: () => void | Promise<void>;
}) {
  const [outGuard, setOutGuard] = useState(data.agent_output_guard_enabled);
  const [humanizer, setHumanizer] = useState(data.agent_humanizer_enabled);
  const [guardReportE164, setGuardReportE164] = useState(
    data.guard_report_whatsapp_e164 ?? "",
  );
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    setOutGuard(data.agent_output_guard_enabled);
    setHumanizer(data.agent_humanizer_enabled);
    setGuardReportE164(data.guard_report_whatsapp_e164 ?? "");
  }, [data]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await adminRequest<AgentPipelineSettings>(
        "/api/admin/settings/agent-pipeline",
        token,
        {
          method: "PUT",
          body: JSON.stringify({
            agent_output_guard_enabled: outGuard,
            agent_humanizer_enabled: humanizer,
            guard_report_whatsapp_e164: guardReportE164,
          }),
        },
      );
      setMsg("Saved");
      await onSaved();
    } catch (x) {
      setMsg(x instanceof Error ? x.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="max-w-lg space-y-4">
      <label className="block text-sm">
        <span className="text-zinc-200">Guard alert WhatsApp (E.164)</span>
        <span className="block text-zinc-500 text-xs mt-0.5 mb-1">
          Send guard alerts to this number when a message is blocked. Leave empty to turn
          alerts off. Example: +2348012345678
        </span>
        <input
          type="text"
          inputMode="tel"
          autoComplete="tel"
          placeholder="+234…"
          className="w-full mt-1 rounded-md bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm"
          value={guardReportE164}
          onChange={(e) => setGuardReportE164(e.target.value)}
        />
      </label>
      <label className="flex items-start gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 shrink-0"
          checked={outGuard}
          onChange={(e) => setOutGuard(e.target.checked)}
        />
        <span>
          <span className="text-zinc-200">Output safety check</span>
          <span className="block text-zinc-500 text-xs mt-0.5">
            Checks outgoing replies for unsafe or internal-only content before delivery.
          </span>
        </span>
      </label>
      <label className="flex items-start gap-2 text-sm cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 shrink-0"
          checked={humanizer}
          onChange={(e) => setHumanizer(e.target.checked)}
        />
        <span>
          <span className="text-zinc-200">Humanize tone</span>
          <span className="block text-zinc-500 text-xs mt-0.5">
            Optional rewrite pass to make replies sound more natural and less robotic.
            Uses <code className="text-zinc-400">OPENAI_HUMANIZER_MODEL</code>.
          </span>
        </span>
      </label>
      {msg && (
        <p
          className={`text-sm ${
            msg === "Saved" ? "text-zinc-300" : "text-zinc-400"
          }`}
        >
          {msg}
        </p>
      )}
      <button
        type="submit"
        disabled={saving}
        className="rounded-md bg-zinc-100 text-zinc-950 text-sm font-medium px-4 py-2 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save agent settings"}
      </button>
    </form>
  );
}

function linkStateLabel(s: string): string {
  switch (s) {
    case "linked":
      return "Linked";
    case "pairing":
      return "Pairing (scan QR)";
    case "unlinked":
    default:
      return "Unlinked";
  }
}

function waMeHrefFromE164(e164: string | null): string | null {
  if (!e164) return null;
  const digits = e164.replace(/\D/g, "");
  if (!digits) return null;
  return `https://wa.me/${digits}`;
}

function WhatsAppLinkPanel({
  data,
  token,
  onSaved,
}: {
  data: WhatsAppSettings;
  token: string;
  onSaved: () => void | Promise<void>;
}) {
  const [pref, setPref] = useState(data.landing_message_prefill);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    setPref(data.landing_message_prefill);
  }, [data.landing_message_prefill]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const base = getApiBaseUrl();
      const r = await fetch(`${base}/api/admin/settings/whatsapp`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ landing_message_prefill: pref }),
      });
      if (!r.ok) throw new Error(await r.text());
      setMsg("Prefill saved.");
      await onSaved();
    } catch (x) {
      setMsg(x instanceof Error ? x.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const st = data.bridge_status || "unknown";
  const waHref = waMeHrefFromE164(data.connected_whatsapp_e164);

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
              data.link_state === "linked"
                ? "bg-white/15 text-white"
                : data.link_state === "pairing"
                  ? "bg-white/10 text-zinc-200"
                  : "bg-zinc-500/20 text-zinc-400"
            }`}
          >
            {linkStateLabel(data.link_state)}
          </span>
          <span
            className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${bridgeBadgeClass(
              st,
            )}`}
          >
            {st}
          </span>
          {data.bridge_updated_at && (
            <span className="text-zinc-500">
              {new Date(data.bridge_updated_at).toLocaleString()}
            </span>
          )}
        </div>
        {data.bridge_message && (
          <p className="mt-2 text-zinc-400 break-words">{data.bridge_message}</p>
        )}
        {st === "unknown" && !data.bridge_updated_at && (
          <p className="mt-2 text-zinc-500 text-sm">
            No bridge status yet. The Node bridge should POST to{" "}
            <code className="text-zinc-300">/api/internal/bridge-status</code>.
          </p>
        )}
      </div>

      {data.link_state === "pairing" && data.qr_data && (
        <div>
          <p className="text-sm text-zinc-400 mb-2">
            Scan this QR code from WhatsApp on your phone to finish linking.
          </p>
          <WhatsAppQr value={data.qr_data} />
        </div>
      )}

      {data.link_state === "linked" && data.connected_whatsapp_e164 && (
        <div className="text-sm space-y-1">
          <p>
            <span className="text-zinc-500">Connected</span>{" "}
            <code className="text-zinc-200">{data.connected_whatsapp_e164}</code>
          </p>
          {waHref && (
            <p>
              <span className="text-zinc-500">Public landing</span>{" "}
              <a
                href={waHref}
                target="_blank"
                rel="noreferrer"
                className="text-zinc-200 hover:underline break-all"
              >
                {waHref}
              </a>{" "}
              (same link used on the homepage)
            </p>
          )}
        </div>
      )}

      {data.link_state === "unlinked" && (
        <p className="text-sm text-zinc-500">
          Start the Whatcommerce bridge. When a QR is available, it will appear here and
          status will switch to &quot;Pairing&quot;.
        </p>
      )}

      <form onSubmit={save} className="space-y-3 max-w-lg border-t border-zinc-800 pt-5">
        <h3 className="text-sm font-medium text-zinc-300">Prefill message (optional)</h3>
        <p className="text-xs text-zinc-500">
          Default text shown when someone opens your public WhatsApp link. Customers can
          still edit it before sending.
        </p>
        <div>
          <label className="text-xs text-zinc-500">Prefill</label>
          <textarea
            className="w-full mt-1 rounded-md bg-zinc-900 border border-zinc-800 px-3 py-2 text-sm min-h-[80px]"
            value={pref}
            onChange={(e) => setPref(e.target.value)}
          />
        </div>
        {msg && (
          <p
            className={`text-sm ${
              msg === "Prefill saved." ? "text-zinc-300" : "text-zinc-400"
            }`}
          >
            {msg}
          </p>
        )}
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-zinc-100 text-zinc-950 text-sm font-medium px-4 py-2 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save prefill message"}
        </button>
      </form>
    </div>
  );
}
