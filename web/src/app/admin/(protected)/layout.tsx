"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ADMIN_ME_REFRESH_EVENT, adminFetch, clearAdminToken, getAdminToken } from "@/lib/admin-api";

type Me = { email?: string; role?: string };

const navClass =
  "rounded-md px-3 py-2 text-sm font-medium text-zinc-400 transition hover:bg-zinc-900 hover:text-zinc-200";
const navActiveClass =
  "rounded-md bg-zinc-800 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:bg-zinc-800";

export default function AdminProtectedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [configErr, setConfigErr] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const loadMe = useCallback(async () => {
    if (!getAdminToken()) {
      router.replace("/admin/login");
      return;
    }
    const res = await adminFetch("/v1/admin/me");
    if (!res.ok) {
      clearAdminToken();
      router.replace("/admin/login");
      return;
    }
    const j = (await res.json()) as Me;
    setMe(j);
    setConfigErr(null);
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadMe();
      } catch (e) {
        if (!cancelled) {
          setConfigErr(e instanceof Error ? e.message : "Configuration error");
        }
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadMe, pathname]);

  useEffect(() => {
    const onRefresh = () => {
      void loadMe();
    };
    window.addEventListener(ADMIN_ME_REFRESH_EVENT, onRefresh);
    return () => window.removeEventListener(ADMIN_ME_REFRESH_EVENT, onRefresh);
  }, [loadMe]);

  function logout() {
    clearAdminToken();
    router.replace("/admin/login");
    router.refresh();
  }

  if (configErr) {
    return (
      <div className="min-h-screen bg-zinc-950 p-8 text-zinc-100">
        <p className="text-red-400">{configErr}</p>
        <p className="mt-2 text-sm text-zinc-500">Set NEXT_PUBLIC_API_URL in web/.env.local to your FastAPI origin.</p>
      </div>
    );
  }

  if (!authChecked || !me) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-500">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="flex w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
        <div className="border-b border-zinc-800 px-4 py-5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">Whatcommerce</p>
          <p className="mt-2 truncate text-sm font-medium text-zinc-200">{me.email}</p>
          <p className="mt-0.5 text-xs text-zinc-600">{me.role}</p>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2">
          <Link
            href="/admin/whatcommerce"
            className={pathname === "/admin/whatcommerce" ? navActiveClass : navClass}
          >
            Platform bot
          </Link>
          {me.role === "super_admin" ? (
            <Link href="/admin/billing" className={pathname === "/admin/billing" ? navActiveClass : navClass}>
              Billing
            </Link>
          ) : null}
          {me.role === "super_admin" ? (
            <Link href="/admin/admins" className={pathname === "/admin/admins" ? navActiveClass : navClass}>
              Admins
            </Link>
          ) : null}
          <Link href="/admin/settings" className={pathname === "/admin/settings" ? navActiveClass : navClass}>
            Account
          </Link>
        </nav>
        <div className="border-t border-zinc-800 p-2">
          <button
            type="button"
            onClick={logout}
            className="w-full rounded-md border border-zinc-800 px-3 py-2 text-left text-sm text-zinc-400 transition hover:border-zinc-700 hover:bg-zinc-900 hover:text-zinc-200"
          >
            Log out
          </button>
        </div>
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <main className="flex-1 overflow-auto bg-zinc-950 px-6 py-8 sm:px-10 lg:px-12">{children}</main>
      </div>
    </div>
  );
}
