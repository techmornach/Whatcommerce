/**
 * Whatcommerce WhatsApp Web bridge (stub)
 *
 * 1) npm install
 * 2) Set API base + INTERNAL_API_KEY in .env (copy from .env.example)
 * 3) node index.mjs  — scan QR, then text messages are POSTed to the API
 *
 * Full OpenAI agent + session store integration comes next.
 */
import http from "http";
import wweb from "whatsapp-web.js";
import qrcode from "qrcode-terminal";

const { Client, LocalAuth } = wweb;
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
function loadEnv() {
  const p = join(__dirname, ".env");
  if (!existsSync(p)) return;
  const s = readFileSync(p, "utf8");
  for (const line of s.split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i === -1) continue;
    const k = t.slice(0, i).trim();
    const v = t.slice(i + 1).trim().replace(/^['"]|['"]$/g, "");
    if (!process.env[k]) process.env[k] = v;
  }
}
loadEnv();

const API_BASE = (process.env.WHATCOMMERCE_API_BASE || "http://127.0.0.1:8000").replace(
  /\/$/,
  ""
);
const INTERNAL_KEY = process.env.INTERNAL_API_KEY || "";
const PUPPETEER_EXECUTABLE_PATH = process.env.PUPPETEER_EXECUTABLE_PATH || "";
const DISPATCH_PORT = process.env.DISPATCH_PORT || "3001";
const MAX_MEDIA_BYTES = 5 * 1024 * 1024;
const BRIDGE_HEARTBEAT_MS = 45_000;

/**
 * @param {object} opts
 * @param {string} opts.status
 * @param {string | null} [opts.message]
 * @param {string | null} [opts.qr_data] — raw QR string when status is qr (admin UI shows same code)
 * @param {string | null} [opts.phone_e164] — include on first ready after pair; omit on heartbeats so the API keeps the stored number
 */
async function postBridgeReport({ status, message, qr_data, phone_e164 }) {
  const body = {
    status,
    message: message == null ? null : String(message).slice(0, 4000),
  };
  if (qr_data != null && String(qr_data).trim()) {
    body.qr_data = String(qr_data).slice(0, 20000);
  }
  if (phone_e164 != null && String(phone_e164).trim()) {
    body.phone_e164 = String(phone_e164).trim().slice(0, 32);
  }
  try {
    await fetch(`${API_BASE}/api/internal/bridge-status`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_KEY,
      },
      body: JSON.stringify(body),
    });
  } catch (e) {
    console.error("bridge-status POST failed", e);
  }
}

function phoneE164FromClientInfo(info) {
  if (!info?.wid) return null;
  const w = info.wid;
  const ser = w._serialized || "";
  const user = ser.includes("@") ? ser.split("@")[0] : w.user;
  if (!user) return null;
  const digits = String(user).replace(/\D/g, "");
  if (!digits) return null;
  return `+${digits}`;
}

if (!INTERNAL_KEY) {
  console.error("Set INTERNAL_API_KEY in .env (must match the API's INTERNAL_API_KEY).");
  process.exit(1);
}

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: join(__dirname, ".wwebjs") }),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
    ...(PUPPETEER_EXECUTABLE_PATH
      ? { executablePath: PUPPETEER_EXECUTABLE_PATH }
      : {}),
  },
});

client.on("qr", (qr) => {
  console.log("Scan this QR with WhatsApp (linked device):");
  qrcode.generate(qr, { small: true });
  postBridgeReport({
    status: "qr",
    message: "Waiting for QR scan",
    qr_data: qr,
  });
});

function startDispatchServer() {
  const port = parseInt(String(DISPATCH_PORT), 10);
  if (Number.isNaN(port) || port <= 0) {
    console.log("Dispatch server disabled (set DISPATCH_PORT=3001 to enable).");
    return;
  }
  http
    .createServer(async (req, res) => {
      if (req.method !== "POST" || req.url !== "/dispatch") {
        res.writeHead(404);
        res.end();
        return;
      }
      let body = "";
      for await (const ch of req) {
        body += ch;
      }
      const key = req.headers["x-internal-key"] || req.headers["X-Internal-Key"];
      if (key !== INTERNAL_KEY) {
        res.writeHead(401, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "unauthorized" }));
        return;
      }
      let json;
      try {
        json = JSON.parse(body || "{}");
      } catch {
        res.writeHead(400);
        res.end();
        return;
      }
      const chatId = json.chat_id || json.chatId;
      const text = json.text;
      if (!chatId || !text) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "chat_id and text required" }));
        return;
      }
      try {
        if (!client.info) {
          res.writeHead(503, { "Content-Type": "application/json" });
          res.end(
            JSON.stringify({
              error: "whatsapp client not ready; wait for bridge ready/heartbeat",
            })
          );
          return;
        }
        const msg = await client.sendMessage(chatId, String(text));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true, id: msg?.id?._serialized || null }));
      } catch (e) {
        const err = e instanceof Error ? e.message : String(e);
        console.error("dispatch send failed", chatId, err, e);
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            error: err,
            chat_id: chatId,
            client_state: client.info ? "ready" : "not_ready",
          })
        );
      }
    })
    .listen(port, "127.0.0.1", () => {
      console.log(`Dispatch server listening http://127.0.0.1:${port}/dispatch`);
    });
}

client.on("authenticated", () => {
  postBridgeReport({ status: "init", message: "Authenticated, loading…" });
});

client.on("auth_failure", (msg) => {
  postBridgeReport({ status: "error", message: `Auth failure: ${msg}` });
});

client.on("disconnected", (reason) => {
  postBridgeReport({ status: "error", message: `Disconnected: ${reason}` });
});

client.on("ready", () => {
  console.log("WhatsApp client is ready");
  const phone = phoneE164FromClientInfo(client.info);
  postBridgeReport({
    status: "ready",
    message: null,
    phone_e164: phone,
  });
  startDispatchServer();
  setInterval(() => {
    postBridgeReport({ status: "ready", message: "heartbeat" });
  }, BRIDGE_HEARTBEAT_MS);
});

client.on("message", async (msg) => {
  if (msg.from === "status@broadcast") return;
  const from = msg.from || "";
  const body = msg.body || "";
  const messageId = msg.id?._serialized || null;
  const messageType = (msg.type || "chat").toString();
  const payload = {
    from_wa_id: from,
    body,
    message_id: messageId,
    message_type: messageType,
  };
  if (msg.hasMedia) {
    try {
      const media = await msg.downloadMedia();
      if (media?.data) {
        const size = Math.floor((media.data.length * 3) / 4);
        if (size > MAX_MEDIA_BYTES) {
          try {
            await client.sendMessage(
              from,
              "That file is too large. Please send something under 5 MB."
            );
          } catch (e) {
            console.error("Failed to send size reply", e);
          }
          return;
        }
        payload.media_mimetype = media.mimetype || null;
        payload.media_base64 = media.data;
      }
    } catch (e) {
      console.error("Media download failed", e);
    }
  }
  try {
    const r = await fetch(`${API_BASE}/api/internal/inbound-messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Key": INTERNAL_KEY,
      },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      console.error("API error", r.status, await r.text());
      return;
    }
    const out = await r.json().catch(() => ({}));
    const replies = Array.isArray(out.replies) ? out.replies : [];
    for (const line of replies) {
      if (!line) continue;
      try {
        await client.sendMessage(msg.from, line);
      } catch (e) {
        console.error("Failed to send reply", e);
      }
    }
    if (replies.length) {
      console.log("Sent", replies.length, "reply(ies) to", from.slice(0, 24));
    } else {
      console.log("No replies from API for", from.slice(0, 20), "…");
    }
  } catch (e) {
    console.error("API unreachable:", e);
  }
});

postBridgeReport({ status: "init", message: "Starting WhatsApp client…" });

client.initialize().catch(async (e) => {
  console.error("Failed to start client:", e);
  try {
    await postBridgeReport({ status: "error", message: String(e) });
  } catch {
    // best effort only
  }
  process.exit(1);
});
