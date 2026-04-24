import express from "express";
import axios from "axios";
import qrcode from "qrcode-terminal";
import { Client, LocalAuth } from "whatsapp-web.js";
import { config } from "./config.js";

const app = express();
app.use(express.json({ limit: "1mb" }));

/** @type {import('whatsapp-web.js').Client | null} */
let client = null;
let clientReady = false;

function buildPuppeteerOptions() {
  const args = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--disable-gpu",
  ];
  const executablePath = config.puppeteerExecutablePath;
  return executablePath ? { args, executablePath } : { args };
}

function createClient() {
  const wa = new Client({
    authStrategy: new LocalAuth({ dataPath: ".wwebjs_auth" }),
    puppeteer: buildPuppeteerOptions(),
  });

  wa.on("qr", (qr) => {
    clientReady = false;
    console.log("[wa-bridge] Scan this QR with WhatsApp (Linked devices):");
    qrcode.generate(qr, { small: true });
  });

  wa.on("authenticated", () => {
    console.log("[wa-bridge] Authenticated");
  });

  wa.on("auth_failure", (m) => {
    console.error("[wa-bridge] auth_failure", m);
    clientReady = false;
  });

  wa.on("ready", () => {
    clientReady = true;
    console.log("[wa-bridge] Client ready");
  });

  wa.on("disconnected", (reason) => {
    clientReady = false;
    console.warn("[wa-bridge] disconnected:", reason);
  });

  wa.on("message", async (msg) => {
    try {
      if (msg.fromMe) return;

      const body = msg.body || "";
      const payload = {
        tenant_id: config.tenantId,
        message_id: msg.id?._serialized || String(msg.id),
        from_id: msg.from,
        from_me: !!msg.fromMe,
        body,
        timestamp: msg.timestamp,
        chat_id: msg.from,
      };

      const url = `${config.apiBaseUrl.replace(/\/$/, "")}/internal/whatsapp/inbound`;
      const resp = await axios.post(url, payload, {
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Token": config.internalSecret,
        },
        timeout: 60_000,
        validateStatus: () => true,
      });
      if (resp.status >= 400) {
        console.error("[wa-bridge] API inbound error:", resp.status, resp.data);
      }
    } catch (err) {
      console.error("[wa-bridge] forward to API failed:", err?.message || err);
    }
  });

  return wa;
}

app.get("/health", (_req, res) => {
  res.json({ status: "ok", whatsapp_ready: clientReady });
});

app.post("/internal/send", (req, res) => {
  const token = req.header("x-internal-token");
  if (!token || token !== config.internalSecret) {
    return res.status(401).json({ detail: "Invalid or missing internal token" });
  }
  if (!client || !clientReady) {
    return res.status(503).json({ detail: "WhatsApp client not ready" });
  }

  const messages = Array.isArray(req.body?.messages) ? req.body.messages : [];
  (async () => {
    for (const m of messages) {
      const to = m?.to;
      const body = m?.body;
      if (!to || typeof body !== "string") continue;
      await client.sendMessage(to, body);
    }
    res.json({ ok: true, sent: messages.length });
  })().catch((e) => {
    console.error("[wa-bridge] send failed:", e);
    if (!res.headersSent) {
      res.status(500).json({ detail: String(e?.message || e) });
    }
  });
});

app.listen(config.bridgePort, config.bridgeHost, () => {
  console.log(`[wa-bridge] HTTP on http://${config.bridgeHost}:${config.bridgePort}`);
  client = createClient();
  client.initialize().catch((e) => {
    console.error("[wa-bridge] initialize failed:", e);
    process.exit(1);
  });
});
