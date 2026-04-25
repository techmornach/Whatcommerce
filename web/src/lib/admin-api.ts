/**
 * Admin dashboard → FastAPI directly (no Next.js /api proxy).
 * JWT lives in sessionStorage (acceptable for an internal admin UI; use BFF + httpOnly cookies if you need stricter XSS isolation).
 */

const STORAGE_KEY = "wc_admin_jwt";

/** Shell listens for this after Account settings save to refetch `/v1/admin/me`. */
export const ADMIN_ME_REFRESH_EVENT = "wc-admin-me-refresh";

export function getPublicApiBase(): string {
  const b = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (!b) {
    throw new Error("NEXT_PUBLIC_API_URL is not set (FastAPI base URL, e.g. http://localhost:8000)");
  }
  return b;
}

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(STORAGE_KEY);
}

export function setAdminToken(token: string) {
  sessionStorage.setItem(STORAGE_KEY, token);
}

export function clearAdminToken() {
  sessionStorage.removeItem(STORAGE_KEY);
}

export async function adminLogin(email: string, password: string) {
  const res = await fetch(`${getPublicApiBase()}/v1/auth/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = (await res.json().catch(() => ({}))) as { access_token?: string; detail?: unknown };
  if (!res.ok) {
    throw new Error(formatApiError(data.detail, "Login failed"));
  }
  if (!data.access_token) throw new Error("No access_token in response");
  setAdminToken(data.access_token);
}

export function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    try {
      return detail.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : JSON.stringify(x))).join("; ");
    } catch {
      return fallback;
    }
  }
  return fallback;
}

/** Authenticated fetch to FastAPI (Bearer from sessionStorage). */
export async function adminFetch(path: string, init: RequestInit = {}) {
  const url = `${getPublicApiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(init.headers);
  const t = getAdminToken();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  if (init.body != null && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(url, { ...init, headers });
}
