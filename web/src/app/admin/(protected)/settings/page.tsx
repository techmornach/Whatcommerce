"use client";

import { useEffect, useState } from "react";
import { ADMIN_ME_REFRESH_EVENT, adminFetch, formatApiError, setAdminToken } from "@/lib/admin-api";

type Me = { id?: string; email?: string; role?: string };

export default function AdminSettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await adminFetch("/v1/admin/me");
      const j = (await res.json().catch(() => ({}))) as Me;
      if (!cancelled && res.ok) {
        setMe(j);
        setEmail(j.email ?? "");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const isSuper = me?.role === "super_admin";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);

    const pw = password.trim();
    const pw2 = password2.trim();
    if (pw || pw2) {
      if (pw.length < 8) {
        setErr("Password must be at least 8 characters.");
        return;
      }
      if (pw !== pw2) {
        setErr("Passwords do not match.");
        return;
      }
    }

    const body: { email?: string; password?: string } = {};
    if (isSuper) {
      const em = email.trim().toLowerCase();
      if (em && em !== (me?.email ?? "").toLowerCase()) {
        body.email = em;
      }
    }
    if (pw) {
      body.password = pw;
    }
    if (!body.email && !body.password) {
      setErr("Change your email and/or password, then save.");
      return;
    }

    setSaving(true);
    try {
      const res = await adminFetch("/v1/admin/me", {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      const j = (await res.json().catch(() => ({}))) as Me & { access_token?: string; detail?: unknown };
      if (!res.ok) {
        setErr(formatApiError(j.detail, "Update failed"));
        return;
      }
      if (j.access_token) {
        setAdminToken(j.access_token);
      }
      setMe(j);
      setEmail(j.email ?? "");
      setPassword("");
      setPassword2("");
      setMsg("Saved.");
      window.dispatchEvent(new Event(ADMIN_ME_REFRESH_EVENT));
    } finally {
      setSaving(false);
    }
  }

  if (!me) {
    return <p className="text-sm text-zinc-500">Loading…</p>;
  }

  return (
    <div className="mx-auto max-w-md space-y-10">
      <header className="border-b border-zinc-800 pb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Account</h1>
        <p className="mt-3 text-sm text-zinc-500">
          {isSuper
            ? "Super admins may update their sign-in email and password."
            : "You can change your password. Ask a super admin to change your email."}
        </p>
      </header>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/20">
        <div className="border-b border-zinc-800 px-5 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Profile</h2>
        </div>
        <form className="space-y-4 p-5" onSubmit={onSubmit}>
          {isSuper ? (
            <div>
              <label className="text-xs font-medium text-zinc-500" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          ) : (
            <div>
              <p className="text-xs font-medium text-zinc-500">Email</p>
              <p className="mt-1 font-mono text-sm text-zinc-300">{me.email}</p>
            </div>
          )}
          <div>
            <label className="text-xs font-medium text-zinc-500" htmlFor="pw">
              New password
            </label>
            <input
              id="pw"
              type="password"
              autoComplete="new-password"
              minLength={8}
              placeholder="Leave blank to keep current"
              className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-zinc-500" htmlFor="pw2">
              Confirm new password
            </label>
            <input
              id="pw2"
              type="password"
              autoComplete="new-password"
              minLength={8}
              className="mt-1 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none ring-zinc-600/30 focus:border-zinc-700 focus:ring-2"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
            />
          </div>
          {err ? <p className="text-sm text-red-400">{err}</p> : null}
          {msg ? <p className="text-sm text-zinc-500">{msg}</p> : null}
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-white disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </form>
      </section>
    </div>
  );
}
