/**
 * Shared whatsapp-web.js → FastAPI bridge.
 * Each worker is a separate Node process with its own WhatsApp session folder.
 */
import qr from "qrcode-terminal";
import pkg from "whatsapp-web.js";
import { readFileSync, rmSync } from "node:fs";
import { join } from "node:path";

const { Client, LocalAuth } = pkg;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Root of the FastAPI app only (no `/v1` suffix — paths add `/v1/...` themselves). */
function normalizeApiBaseUrl(raw) {
  let u = (raw || "http://localhost:8000").replace(/\/$/, "");
  if (/\/v1$/i.test(u)) {
    console.warn(
      "[bridge] API_BASE_URL should not end with /v1; stripping it (was %s → %s)",
      u,
      u.replace(/\/v1$/i, ""),
    );
    u = u.replace(/\/v1$/i, "");
  }
  return u;
}

export function loadDotEnv(envFilePath) {
  try {
    const raw = readFileSync(envFilePath, "utf8");
    for (const line of raw.split("\n")) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const i = t.indexOf("=");
      if (i === -1) continue;
      const k = t.slice(0, i).trim();
      let v = t.slice(i + 1).trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        v = v.slice(1, -1);
      }
      if (!process.env[k]) process.env[k] = v;
    }
  } catch {
    /* optional .env */
  }
}

/**
 * @param {object} opts
 * @param {string} opts.workerRoot Absolute path to the worker directory (contains .env and session data).
 * @param {"whatcommerce"|"store_manager"} opts.channel Sent to the API on every message.
 * @param {string} opts.label Log label for operators.
 */
export function startWorker({ workerRoot, channel, label }) {
  const envPath = join(workerRoot, ".env");
  loadDotEnv(envPath);

  const API_BASE_URL = normalizeApiBaseUrl(process.env.API_BASE_URL);
  const INTERNAL_API_SECRET = process.env.INTERNAL_API_SECRET || "";
  const sessionPath = join(workerRoot, ".wwebjs_auth");
  const tenantId = (process.env.TENANT_ID || "").trim();
  const outboundPollMs = Math.max(
    5000,
    Number.parseInt(process.env.OUTBOUND_POLL_MS || "20000", 10) || 20000,
  );
  const outboundAckRetries = Math.min(
    20,
    Math.max(3, Number.parseInt(process.env.OUTBOUND_ACK_RETRIES || "10", 10) || 10),
  );
  const sessionResetPollMs = Math.max(
    5000,
    Number.parseInt(process.env.SESSION_RESET_POLL_MS || "12000", 10) || 12000,
  );

  let client = null;
  let outboundIntervalId = null;
  let adminResetBusy = false;

  function createClient() {
    return new Client({
      authStrategy: new LocalAuth({ dataPath: sessionPath }),
      puppeteer: {
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
      },
    });
  }

  async function pushWhatcommerceQrToApi(qrData) {
    if (channel !== "whatcommerce") return;
    const raw = String(qrData || "");
    if (!raw) return;
    const url = `${API_BASE_URL}/v1/internal/whatcommerce/qr`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Secret": INTERNAL_API_SECRET,
        },
        body: JSON.stringify({ qr: raw.slice(0, 8192) }),
      });
      if (!res.ok) {
        console.warn("[%s] qr upload failed", label, res.status, await res.text());
      }
    } catch (e) {
      console.warn("[%s] qr upload error", label, e);
    }
  }

  async function reportWhatcommerceSessionReady() {
    if (channel !== "whatcommerce" || !client) return;
    const widUser = client.info?.wid?.user;
    const digits = String(widUser || "").replace(/\D/g, "");
    if (!digits || digits.length < 10) {
      console.warn("[%s] session-ready skipped: invalid WhatsApp user id", label);
      return;
    }
    const url = `${API_BASE_URL}/v1/internal/whatcommerce/session-ready`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Secret": INTERNAL_API_SECRET,
        },
        body: JSON.stringify({ whatsapp_user_e164: digits }),
      });
      const text = await res.text();
      if (!res.ok) {
        console.error("[%s] session-ready failed", label, res.status, text, "url=", url);
        return;
      }
      console.log("[%s] session-ready ok (platform Whatcommerce WA)", label, text);
    } catch (e) {
      console.error("[%s] session-ready error", label, e);
    }
  }

  async function registerStoreManagerSession(loggedInUser) {
    if (channel !== "store_manager" || !tenantId) return;
    const digits = String(loggedInUser || "").replace(/\D/g, "");
    if (!digits || digits.length < 10) {
      console.warn("[%s] register-session skipped: invalid WhatsApp user id", label);
      return;
    }
    const url = `${API_BASE_URL}/v1/internal/store-manager/register-session`;
    const body = { tenant_id: tenantId, store_manager_phone_e164: digits };
    const waLinkRaw = (process.env.WA_LINK_TOKEN || "").trim();
    if (waLinkRaw) {
      if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(waLinkRaw)) {
        body.wa_link_token = waLinkRaw;
      } else {
        console.warn("[%s] WA_LINK_TOKEN is not a valid UUID; omitting from register-session", label);
      }
    }
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Secret": INTERNAL_API_SECRET,
        },
        body: JSON.stringify(body),
      });
      const text = await res.text();
      if (!res.ok) {
        console.error("[%s] register-session failed", label, res.status, text);
        return;
      }
      let parsed = {};
      try {
        if (text) parsed = JSON.parse(text);
      } catch {
        parsed = { raw: text };
      }
      console.log("[%s] register-session ok", label, parsed);
    } catch (e) {
      console.error("[%s] register-session error", label, e);
    }
  }

  async function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Secret": INTERNAL_API_SECRET,
      },
      body: JSON.stringify(body),
    });
  }

  async function runOutboundOnce() {
    const isPlatform = channel === "whatcommerce";
    if (channel !== "whatcommerce" && channel !== "store_manager") return;
    if (!isPlatform && !tenantId) return;
    if (!client) return;

    const base = isPlatform ? "whatcommerce" : "store-manager";
    const claimUrl = `${API_BASE_URL}/v1/internal/${base}/outbound/claim`;
    const ackUrl = `${API_BASE_URL}/v1/internal/${base}/outbound/ack`;
    const failUrl = `${API_BASE_URL}/v1/internal/${base}/outbound/report-fail`;
    const forgiveUrl = `${API_BASE_URL}/v1/internal/${base}/outbound/forgive`;

    const claimBody = isPlatform ? { limit: 15 } : { tenant_id: tenantId, limit: 15 };

    try {
      const res = await postJson(claimUrl, claimBody);
      const text = await res.text();
      if (!res.ok) {
        console.error("[%s] outbound/claim failed", label, res.status, text, "url=", claimUrl);
        return;
      }
      const data = JSON.parse(text);
      const items = Array.isArray(data.items) ? data.items : [];
      for (const row of items) {
        const digits = String(row.to_phone_e164 || "").replace(/\D/g, "");
        if (!digits || !row.body) continue;
        const jid = `${digits}@c.us`;
        try {
          await client.sendMessage(jid, String(row.body));
        } catch (sendErr) {
          const msg = sendErr instanceof Error ? sendErr.message : String(sendErr);
          console.error("[%s] outbound send failed", label, sendErr);
          const failBody = isPlatform
            ? { ids: [row.id], error: msg.slice(0, 2000), failure_class: "send" }
            : { tenant_id: tenantId, ids: [row.id], error: msg.slice(0, 2000), failure_class: "send" };
          try {
            const fr = await postJson(failUrl, failBody);
            if (!fr.ok) console.error("[%s] outbound/report-fail failed", label, fr.status, await fr.text());
          } catch (e) {
            console.error("[%s] outbound/report-fail error", label, e);
          }
          continue;
        }

        const ackBody = isPlatform ? { ids: [row.id] } : { tenant_id: tenantId, ids: [row.id] };
        let acked = false;
        for (let i = 0; i < outboundAckRetries; i++) {
          try {
            const ackRes = await postJson(ackUrl, ackBody);
            if (ackRes.ok) {
              acked = true;
              break;
            }
            const ackText = await ackRes.text();
            console.warn("[%s] outbound/ack retry %s/%s", label, i + 1, outboundAckRetries, ackRes.status, ackText);
          } catch (ackErr) {
            console.warn("[%s] outbound/ack retry error", label, i + 1, ackErr);
          }
          await sleep(400 + i * 150);
        }

        if (!acked) {
          console.error("[%s] outbound/ack exhausted; forgiving row to avoid duplicate send", label, row.id);
          const forgiveBody = isPlatform ? { ids: [row.id] } : { tenant_id: tenantId, ids: [row.id] };
          try {
            const gr = await postJson(forgiveUrl, forgiveBody);
            if (!gr.ok) console.error("[%s] outbound/forgive failed", label, gr.status, await gr.text());
          } catch (e) {
            console.error("[%s] outbound/forgive error", label, e);
          }
        }
      }
    } catch (e) {
      console.error("[%s] outbound poll error", label, e);
    }
  }

  async function forwardToApi(from, text) {
    const url = `${API_BASE_URL}/v1/internal/whatsapp/inbound`;
    /** One store-manager process = one tenant UUID; keeps many shops from mixing in the API. */
    const payload = {
      channel,
      from_e164: from.replace(/\D/g, ""),
      text,
    };
    if (channel === "store_manager" && tenantId) {
      payload.tenant_hint = tenantId;
    }
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Secret": INTERNAL_API_SECRET,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text();
      console.error("API error", res.status, errText);
      return [];
    }
    const data = await res.json();
    console.log("API response", data);
    const replies = Array.isArray(data.replies) ? data.replies : [];
    return replies;
  }

  async function hardWhatcommerceSessionReset() {
    console.warn(
      "[%s] admin requested session replacement — stopping client, deleting %s, then showing QR again",
      label,
      sessionPath,
    );
    if (outboundIntervalId) {
      clearInterval(outboundIntervalId);
      outboundIntervalId = null;
    }
    const prev = client;
    client = null;
    if (prev) {
      try {
        await prev.destroy();
      } catch (e) {
        console.warn("[%s] client.destroy during session reset (may be harmless)", label, e);
      }
    }
    try {
      rmSync(sessionPath, { recursive: true, force: true });
    } catch (e) {
      console.warn("[%s] could not fully remove session folder", label, e);
    }
    const ackUrl = `${API_BASE_URL}/v1/internal/whatcommerce/session-reset-ack`;
    let acked = false;
    for (let i = 0; i < 15; i++) {
      try {
        const ackRes = await fetch(ackUrl, {
          method: "POST",
          headers: { "X-Internal-Secret": INTERNAL_API_SECRET },
        });
        if (ackRes.ok) {
          acked = true;
          break;
        }
        console.warn("[%s] session-reset-ack attempt %s → %s", label, i + 1, ackRes.status);
      } catch (e) {
        console.warn("[%s] session-reset-ack attempt %s error", label, i + 1, e);
      }
      await sleep(300 + i * 120);
    }
    if (!acked) {
      console.error(
        "[%s] session-reset-ack failed after retries — exiting so the process supervisor can restart you (check INTERNAL_API_SECRET / API reachability)",
        label,
      );
      process.exit(1);
    }

    client = createClient();
    wireClient(client);
    await client.initialize();
  }

  async function pollAdminSessionReset() {
    if (channel !== "whatcommerce" || adminResetBusy) return;
    try {
      const url = `${API_BASE_URL}/v1/internal/whatcommerce/session-control`;
      const res = await fetch(url, { headers: { "X-Internal-Secret": INTERNAL_API_SECRET } });
      if (!res.ok) return;
      const j = await res.json();
      if (!j.whatcommerce_pending_session_reset) return;
      adminResetBusy = true;
      await hardWhatcommerceSessionReset();
    } catch (e) {
      console.error("[%s] session-control poll error", label, e);
    } finally {
      adminResetBusy = false;
    }
  }

  function wireClient(c) {
    c.on("qr", (qrData) => {
      qr.generate(qrData, { small: true });
      if (channel === "whatcommerce") {
        void pushWhatcommerceQrToApi(qrData);
      }
    });

    c.on("ready", async () => {
      console.log("[%s] WhatsApp ready (channel=%s, session=%s)", label, channel, sessionPath);
      if (channel === "store_manager") {
        const widUser = c.info?.wid?.user;
        await registerStoreManagerSession(widUser);
      }
      if (channel === "whatcommerce") {
        await reportWhatcommerceSessionReady();
      }
      if (outboundIntervalId) {
        clearInterval(outboundIntervalId);
        outboundIntervalId = null;
      }
      await runOutboundOnce();
      outboundIntervalId = setInterval(runOutboundOnce, outboundPollMs);
    });

    c.on("message", async (msg) => {
      if (msg.from === "status@broadcast") return;
      const jidUser = msg.from.split("@")[0] || "";
      const body = msg.body || "";
      console.log("[%s] inbound", label, { from: jidUser, len: body.length });
      try {
        const replies = await forwardToApi(jidUser, body);
        if (replies && replies.length > 0) {
          for (const chunk of replies) {
            if (chunk && String(chunk).trim()) {
              await msg.reply(String(chunk));
            }
          }
        }
        void runOutboundOnce();
      } catch (e) {
        console.error(e);
      }
    });
  }

  client = createClient();
  wireClient(client);
  client.initialize().catch((e) => {
    console.error("Failed to start client", e);
    process.exit(1);
  });

  if (channel === "whatcommerce") {
    setInterval(pollAdminSessionReset, sessionResetPollMs);
  }
}
