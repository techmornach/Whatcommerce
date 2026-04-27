const DEFAULT_API = "http://127.0.0.1:8000";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const w = window as unknown as { __API__?: string };
    if (w.__API__) return w.__API__;
  }
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || DEFAULT_API;
}

export type PublicConfig = {
  whatsapp_e164: string;
  whatsapp_href: string;
  message_prefill: string;
  bot_connected: boolean;
  link_state: string;
};

export async function fetchPublicConfig(): Promise<PublicConfig | null> {
  const base = getApiBaseUrl();
  try {
    const r = await fetch(`${base}/api/public/config`, {
      next: { revalidate: 30 },
    });
    if (!r.ok) return null;
    return (await r.json()) as PublicConfig;
  } catch {
    return null;
  }
}

export const AUTH_TOKEN_KEY = "wc_admin_token";

export async function adminLogin(
  email: string,
  password: string
): Promise<{ access_token: string; expires_in: number }> {
  const base = getApiBaseUrl();
  const r = await fetch(`${base}/api/admin/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || "Login failed");
  }
  return (await r.json()) as { access_token: string; expires_in: number };
}

export async function adminFetch<T>(path: string, token: string | null): Promise<T> {
  const base = getApiBaseUrl();
  const r = await fetch(`${base}${path}`, {
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
    },
    cache: "no-store",
  });
  if (r.status === 401) throw new Error("unauthorized");
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as T;
}

export async function adminRequest<T>(
  path: string,
  token: string | null,
  init: RequestInit
): Promise<T> {
  const base = getApiBaseUrl();
  const method = (init.method || "GET").toUpperCase();
  const extra = (init.headers || {}) as Record<string, string>;
  const headers: Record<string, string> = {
    Authorization: token ? `Bearer ${token}` : "",
    ...extra,
  };
  if (method !== "GET" && method !== "DELETE" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const r = await fetch(`${base}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (r.status === 401) throw new Error("unauthorized");
  if (r.status === 204) {
    return undefined as T;
  }
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as T;
}

export async function adminUpload<T>(
  path: string,
  token: string | null,
  formData: FormData
): Promise<T> {
  const base = getApiBaseUrl();
  const r = await fetch(`${base}${path}`, {
    method: "POST",
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: formData,
    cache: "no-store",
  });
  if (r.status === 401) throw new Error("unauthorized");
  if (!r.ok) {
    const raw = await r.text();
    let msg = raw;
    try {
      const j = JSON.parse(raw) as { detail?: unknown };
      if (typeof j.detail === "string") {
        msg = j.detail;
      } else if (Array.isArray(j.detail)) {
        msg = j.detail.map(String).join(" ");
      }
    } catch {}
    throw new Error(msg || "Upload failed");
  }
  return (await r.json()) as T;
}
