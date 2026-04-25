"use client";

import { useEffect, useState } from "react";
import { ConfirmDialog } from "@/components/admin/ConfirmDialog";
import { adminFetch, formatApiError } from "@/lib/admin-api";

type Me = { id?: string; role?: string };
type AdminRow = { id: string; email: string; role: string; is_active: boolean };

export default function AdminsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [rows, setRows] = useState<AdminRow[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "super_admin">("admin");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [deactivateBusy, setDeactivateBusy] = useState(false);

  async function load() {
    setErr(null);
    const m = await adminFetch("/v1/admin/me");
    const mj = await m.json().catch(() => ({}));
    if (!m.ok) {
      setErr("Not authenticated");
      return;
    }
    setMe(mj);
    if (mj.role !== "super_admin") {
      setErr("Only super admins can manage admins.");
      setRows([]);
      return;
    }
    const r = await adminFetch("/v1/admin/admins");
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      setErr(formatApiError((j as { detail?: unknown }).detail, "Failed to load admins"));
      return;
    }
    setRows(Array.isArray(j.admins) ? j.admins : []);
  }

  useEffect(() => {
    void load();
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    const res = await adminFetch("/v1/admin/admins", {
      method: "POST",
      body: JSON.stringify({ email, password, role }),
    });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(formatApiError((j as { detail?: unknown }).detail, "Create failed"));
      return;
    }
    setMsg(`Created ${j.email}`);
    setEmail("");
    setPassword("");
    setRole("admin");
    await load();
  }

  async function confirmDeactivate() {
    if (!deactivateId) return;
    setDeactivateBusy(true);
    setErr(null);
    try {
      const res = await adminFetch(`/v1/admin/admins/${deactivateId}/deactivate`, { method: "POST" });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(formatApiError((j as { detail?: unknown }).detail, "Deactivate failed"));
        return;
      }
      setDeactivateId(null);
      await load();
    } finally {
      setDeactivateBusy(false);
    }
  }

  if (err && !rows.length && me?.role !== "super_admin") {
    return <p className="text-sm text-red-400">{err}</p>;
  }

  const deactivateRow = deactivateId ? rows.find((r) => r.id === deactivateId) : null;

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <ConfirmDialog
        open={Boolean(deactivateId)}
        title="Deactivate admin?"
        description={
          deactivateRow ? (
            <>
              <span className="font-mono text-zinc-300">{deactivateRow.email}</span> will no longer be able to sign in.
            </>
          ) : null
        }
        tone="danger"
        confirmLabel="Deactivate"
        busy={deactivateBusy}
        onClose={() => {
          if (!deactivateBusy) setDeactivateId(null);
        }}
        onConfirm={() => void confirmDeactivate()}
      />
      <header className="border-b border-zinc-800 pb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Admins</h1>
        <p className="mt-3 text-sm text-zinc-500">Platform operators — not tenant store managers.</p>
      </header>

      {err ? <p className="text-sm text-red-400">{err}</p> : null}
      {msg ? <p className="text-sm text-zinc-500">{msg}</p> : null}

      {me?.role === "super_admin" ? (
        <>
          <section className="rounded-lg border border-zinc-800 bg-zinc-900/20">
            <div className="border-b border-zinc-800 px-5 py-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Invite admin</h2>
            </div>
            <form className="space-y-3 p-5 sm:max-w-md" onSubmit={onCreate}>
              <input
                type="email"
                required
                placeholder="Email"
                className="w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                type="password"
                required
                minLength={8}
                placeholder="Password (min 8)"
                className="w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <select
                className="w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-zinc-700"
                value={role}
                onChange={(e) => setRole(e.target.value as "admin" | "super_admin")}
              >
                <option value="admin">admin</option>
                <option value="super_admin">super_admin</option>
              </select>
              <button
                type="submit"
                className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-white"
              >
                Create
              </button>
            </form>
          </section>

          <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/20">
            <div className="border-b border-zinc-800 px-5 py-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Directory</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-xs font-medium uppercase tracking-wide text-zinc-600">
                    <th className="px-5 py-3">Email</th>
                    <th className="px-5 py-3">Role</th>
                    <th className="px-5 py-3">Active</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/80">
                  {rows.map((a) => (
                    <tr key={a.id} className="text-zinc-300">
                      <td className="px-5 py-3 font-mono text-sm text-zinc-200">{a.email}</td>
                      <td className="px-5 py-3 text-zinc-500">{a.role}</td>
                      <td className="px-5 py-3 text-zinc-500">{a.is_active ? "Yes" : "No"}</td>
                      <td className="px-5 py-3 text-right">
                        {a.is_active && a.id !== me?.id ? (
                          <button
                            type="button"
                            className="text-xs text-zinc-500 underline-offset-2 hover:text-red-400 hover:underline"
                            onClick={() => setDeactivateId(a.id)}
                          >
                            Deactivate
                          </button>
                        ) : a.is_active && a.id === me?.id ? (
                          <span className="text-xs text-zinc-600">You</span>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
