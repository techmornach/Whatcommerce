"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import QRCode from "react-qr-code";
import { ConfirmDialog } from "@/components/admin/ConfirmDialog";
import { adminFetch, formatApiError } from "@/lib/admin-api";
import { formatAdminDateTime } from "@/lib/format-datetime";

type Platform = {
  knowledge_base_text?: string | null;
  whatcommerce_session_phone_e164?: string | null;
  whatcommerce_session_ready_at?: string | null;
  whatcommerce_pending_session_reset?: boolean;
  whatcommerce_qr_data?: string | null;
};

export default function WhatcommercePlatformPage() {
  const [data, setData] = useState<Platform | null>(null);
  const [kb, setKb] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [sessionConfirmOpen, setSessionConfirmOpen] = useState(false);

  const loadPlatform = useCallback(async (): Promise<boolean> => {
    setErr(null);
    const res = await adminFetch("/v1/admin/platform");
    const j = (await res.json().catch(() => ({}))) as Platform & { detail?: unknown };
    if (!res.ok) {
      setErr(formatApiError(j.detail, "Failed to load"));
      return false;
    }
    setData(j);
    setKb(j.knowledge_base_text ?? "");
    return true;
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await loadPlatform();
      if (!cancelled && !ok) {
        /* err set */
      }
    })().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [loadPlatform]);

  const shouldPollPlatform = useMemo(() => {
    if (loading || !data) return false;
    const noPhone = !data.whatcommerce_session_phone_e164;
    const pending = Boolean(data.whatcommerce_pending_session_reset);
    const hasQr = Boolean(data.whatcommerce_qr_data && data.whatcommerce_qr_data.length > 0);
    return noPhone || pending || hasQr;
  }, [
    loading,
    data?.whatcommerce_session_phone_e164,
    data?.whatcommerce_pending_session_reset,
    data?.whatcommerce_qr_data,
  ]);

  useEffect(() => {
    if (!shouldPollPlatform) return undefined;
    const id = setInterval(() => {
      void (async () => {
        const res = await adminFetch("/v1/admin/platform");
        const j = (await res.json().catch(() => ({}))) as Platform;
        if (res.ok) setData(j);
      })();
    }, 2500);
    return () => clearInterval(id);
  }, [shouldPollPlatform]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    const res = await adminFetch("/v1/admin/platform", {
      method: "PATCH",
      body: JSON.stringify({
        knowledge_base_text: kb.trim() || null,
      }),
    });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) {
      setErr(formatApiError((j as { detail?: unknown }).detail, "Save failed"));
      return;
    }
    setData(j);
    setMsg("Saved.");
  }

  async function requestSessionReplacement() {
    setSessionBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const res = await adminFetch("/v1/admin/platform/whatcommerce-session-replacement", {
        method: "POST",
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(formatApiError((j as { detail?: unknown }).detail, "Request failed"));
        return;
      }
      setData(j);
      setSessionConfirmOpen(false);
      setMsg(
        "Session replacement started. A QR will appear below when the worker picks it up (keep npm run start:whatcommerce running).",
      );
    } finally {
      setSessionBusy(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-zinc-500">Loading…</p>;
  }

  const lastReady = formatAdminDateTime(data?.whatcommerce_session_ready_at ?? null);
  const qrValue = data?.whatcommerce_qr_data?.trim() ?? "";

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <ConfirmDialog
        open={sessionConfirmOpen}
        title="Replace WhatsApp session?"
        description={
          <>
            The whatcommerce worker will log out and delete its saved session on this machine, then show a new
            pairing QR <strong className="text-zinc-300">here in the admin</strong> (and still in the terminal). Use
            this if the session was removed in Linked devices or is invalid.
            <span className="mt-2 block text-zinc-500">
              The worker process must be running — it checks the API every few seconds.
            </span>
          </>
        }
        tone="danger"
        confirmLabel="Replace session"
        busy={sessionBusy}
        onClose={() => {
          if (!sessionBusy) setSessionConfirmOpen(false);
        }}
        onConfirm={() => void requestSessionReplacement()}
      />
      <header className="border-b border-zinc-800 pb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Platform WhatsApp</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-zinc-500">
          Global whatcommerce worker session — onboarding, billing, and owner notifications. Not a tenant store line.
          Run{" "}
          <code className="rounded bg-zinc-900 px-1.5 py-0.5 font-mono text-xs text-zinc-400">
            npm run start:whatcommerce
          </code>{" "}
          on the server, then scan the QR below (or replace the session to get a new one).
        </p>
      </header>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/20">
        <div className="flex flex-col gap-3 border-b border-zinc-800 px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Session</h2>
            <p className="mt-1 text-xs text-zinc-600">Reported by the worker when WhatsApp is ready.</p>
          </div>
          <button
            type="button"
            disabled={sessionBusy}
            onClick={() => setSessionConfirmOpen(true)}
            className="shrink-0 rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:border-zinc-600 hover:bg-zinc-900 disabled:opacity-50"
          >
            Replace session (new QR)
          </button>
        </div>
        {data?.whatcommerce_pending_session_reset ? (
          <p className="border-b border-zinc-800/80 bg-zinc-900/40 px-5 py-3 text-xs text-zinc-500">
            Replacement queued — the worker will wipe its local session and post a new QR here when ready.
          </p>
        ) : null}
        {qrValue ? (
          <div className="border-b border-zinc-800/80 px-5 py-6">
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">Pairing QR</p>
            <p className="mt-1 text-xs text-zinc-600">
              WhatsApp → Settings → Linked devices → Link a device → scan this code.
            </p>
            <div className="mt-4 inline-block rounded-lg border border-zinc-700 bg-zinc-950 p-4">
              <QRCode value={qrValue} size={220} level="M" fgColor="#fafafa" bgColor="#09090b" />
            </div>
          </div>
        ) : !data?.whatcommerce_session_phone_e164 ? (
          <p className="border-b border-zinc-800/80 px-5 py-4 text-xs text-zinc-600">
            Waiting for a QR from the whatcommerce worker… If nothing appears, confirm the worker is running and
            logged into the same API (<code className="text-zinc-500">INTERNAL_API_SECRET</code> /{" "}
            <code className="text-zinc-500">API_BASE_URL</code>).
          </p>
        ) : null}
        <dl className="divide-y divide-zinc-800/80 px-5 py-1 text-sm">
          <div className="flex flex-col gap-1 py-4 sm:flex-row sm:items-baseline sm:gap-8">
            <dt className="w-40 shrink-0 text-xs font-medium uppercase tracking-wide text-zinc-600">Phone</dt>
            <dd className="font-mono text-zinc-200">{data?.whatcommerce_session_phone_e164 ?? "—"}</dd>
          </div>
          <div className="flex flex-col gap-1 py-4 sm:flex-row sm:items-baseline sm:gap-8">
            <dt className="w-40 shrink-0 text-xs font-medium uppercase tracking-wide text-zinc-600">Last ready</dt>
            <dd className="text-zinc-300">{lastReady}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/20">
        <div className="border-b border-zinc-800 px-5 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">Bot knowledge</h2>
          <p className="mt-1 text-xs text-zinc-600">Plain text FAQ / policy injected into the platform assistant.</p>
        </div>
        <form className="space-y-4 p-5" onSubmit={onSave}>
          <textarea
            id="kb"
            rows={14}
            className="w-full resize-y rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-200 outline-none ring-zinc-600/40 placeholder:text-zinc-700 focus:border-zinc-700 focus:ring-2"
            placeholder="Pricing, refund policy, supported countries…"
            value={kb}
            onChange={(e) => setKb(e.target.value)}
          />
          {err ? <p className="text-sm text-red-400">{err}</p> : null}
          {msg ? <p className="text-sm text-zinc-500">{msg}</p> : null}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              className="rounded-md bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 transition hover:bg-white"
            >
              Save changes
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
