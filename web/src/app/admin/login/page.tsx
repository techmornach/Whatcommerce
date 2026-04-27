"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { adminLogin, AUTH_TOKEN_KEY } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const t = await adminLogin(email, password);
      if (typeof window !== "undefined") {
        localStorage.setItem(AUTH_TOKEN_KEY, t.access_token);
      }
      router.push("/admin");
    } catch (c) {
      setErr(c instanceof Error ? c.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="wc-shell flex items-center justify-center p-6">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg dark:border-slate-800 dark:bg-slate-900 md:grid-cols-2">
        <div className="hidden bg-gradient-to-br from-teal-700 via-teal-600 to-cyan-600 p-8 text-white md:block">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/80">
            Whatcommerce Admin
          </p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight">
            Run your WhatsApp storefront from one dashboard.
          </h1>
          <p className="mt-4 text-sm text-white/85">
            Manage tenants, plans, knowledge, and bridge status without jumping between
            tools.
          </p>
        </div>

        <div className="p-7 md:p-9">
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Admin access</h1>
          <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
            Sign in to continue.
          </p>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs text-slate-600 dark:text-slate-400">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="wc-input"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-600 dark:text-slate-400">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="wc-input"
                required
              />
            </div>
            {err && <p className="text-sm text-red-500">{err}</p>}
            <button type="submit" disabled={loading} className="wc-btn-primary w-full disabled:opacity-50">
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            <Link href="/" className="hover:text-slate-700 dark:hover:text-slate-200">
              Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
