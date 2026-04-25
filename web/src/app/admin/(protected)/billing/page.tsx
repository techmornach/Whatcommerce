"use client";

import { useEffect, useState } from "react";
import { adminFetch, formatApiError } from "@/lib/admin-api";

type Me = { role?: string };
type Plan = {
  tier: string;
  monthly_amount_ngn: number;
  yearly_amount_ngn: number | null;
  max_products: number;
  max_users: number;
  is_active: boolean;
};

function fmtNgn(n: number) {
  return `₦${n.toLocaleString()}`;
}

export default function BillingPlansPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busyTier, setBusyTier] = useState<string | null>(null);

  async function load() {
    setErr(null);
    setMsg(null);
    const m = await adminFetch("/v1/admin/me");
    const mj = await m.json().catch(() => ({}));
    if (!m.ok) {
      setErr("Not authenticated");
      return;
    }
    setMe(mj);
    if (mj.role !== "super_admin") {
      setErr("Only super admins can edit billing plans.");
      setPlans([]);
      return;
    }
    const r = await adminFetch("/v1/admin/billing/plans");
    const j = (await r.json().catch(() => ({}))) as { plans?: Plan[]; detail?: unknown };
    if (!r.ok) {
      setErr(formatApiError(j.detail, "Failed to load plans"));
      return;
    }
    setPlans(Array.isArray(j.plans) ? j.plans : []);
  }

  useEffect(() => {
    void load();
  }, []);

  function setField(tier: string, patch: Partial<Plan>) {
    setPlans((prev) => prev.map((p) => (p.tier === tier ? { ...p, ...patch } : p)));
  }

  async function savePlan(tier: string) {
    const p = plans.find((x) => x.tier === tier);
    if (!p) return;
    setBusyTier(tier);
    setErr(null);
    setMsg(null);
    try {
      const res = await adminFetch(`/v1/admin/billing/plans/${tier}`, {
        method: "PATCH",
        body: JSON.stringify({
          monthly_amount_ngn: p.monthly_amount_ngn,
          yearly_amount_ngn: p.yearly_amount_ngn,
          max_products: p.max_products,
          max_users: p.max_users,
          is_active: p.is_active,
        }),
      });
      const j = (await res.json().catch(() => ({}))) as Plan & { detail?: unknown };
      if (!res.ok) {
        setErr(formatApiError(j.detail, "Save failed"));
        return;
      }
      setField(tier, j);
      setMsg(`Saved ${tier}.`);
    } finally {
      setBusyTier(null);
    }
  }

  if (err && me?.role !== "super_admin") {
    return <p className="text-sm text-red-400">{err}</p>;
  }

  return (
    <div className="mx-auto max-w-4xl space-y-10">
      <header className="border-b border-zinc-800 pb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Billing plans</h1>
        <p className="mt-3 text-sm text-zinc-500">Pricing and limits used by onboarding, Paystack, and product caps.</p>
      </header>

      {err ? <p className="text-sm text-red-400">{err}</p> : null}
      {msg ? <p className="text-sm text-zinc-500">{msg}</p> : null}

      <div className="space-y-6">
        {plans.map((p) => {
          const busy = busyTier === p.tier;
          return (
            <section key={p.tier} className="rounded-lg border border-zinc-800 bg-zinc-900/20">
              <div className="flex flex-col gap-3 border-b border-zinc-800 px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">{p.tier}</h2>
                  <p className="mt-1 text-xs text-zinc-600">
                    Monthly {fmtNgn(p.monthly_amount_ngn)} · Yearly{" "}
                    {p.yearly_amount_ngn != null ? fmtNgn(p.yearly_amount_ngn) : fmtNgn(p.monthly_amount_ngn * 12)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void savePlan(p.tier)}
                  disabled={busy}
                  className="shrink-0 rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-white disabled:opacity-50"
                >
                  {busy ? "Saving…" : "Save"}
                </button>
              </div>

              <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
                <label className="block">
                  <span className="text-xs font-medium text-zinc-500">Monthly (NGN)</span>
                  <input
                    type="number"
                    min={0}
                    className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                    value={p.monthly_amount_ngn}
                    onChange={(e) => setField(p.tier, { monthly_amount_ngn: Number(e.target.value) })}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-zinc-500">Yearly (NGN)</span>
                  <input
                    type="number"
                    min={0}
                    placeholder="Leave blank to use 12× monthly"
                    className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                    value={p.yearly_amount_ngn ?? ""}
                    onChange={(e) =>
                      setField(p.tier, { yearly_amount_ngn: e.target.value === "" ? null : Number(e.target.value) })
                    }
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-zinc-500">Max products</span>
                  <input
                    type="number"
                    min={0}
                    className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                    value={p.max_products}
                    onChange={(e) => setField(p.tier, { max_products: Number(e.target.value) })}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-zinc-500">Max users</span>
                  <input
                    type="number"
                    min={0}
                    className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                    value={p.max_users}
                    onChange={(e) => setField(p.tier, { max_users: Number(e.target.value) })}
                  />
                </label>
                <label className="flex items-center gap-2 pt-6 text-sm text-zinc-300">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-zinc-700 bg-zinc-950"
                    checked={p.is_active}
                    onChange={(e) => setField(p.tier, { is_active: e.target.checked })}
                  />
                  Active
                </label>
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

