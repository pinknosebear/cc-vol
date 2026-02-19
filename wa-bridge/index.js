import makeWASocket, { useMultiFileAuthState, DisconnectReason } from "@whiskeysockets/baileys";
import pino from "pino";
import express from "express";
import qrcode from "qrcode-terminal";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function normalizeServiceUrl(raw, fallback, defaultInternalPort) {
  let value = (raw || "").trim().replace(/^["']|["']$/g, "");
  if (!value) return fallback;

  // Railway UI can inject labels like "(line 8080)" when selecting hosts.
  value = value.replace(/\s*\(line\s*\d+\)\s*$/i, "");

  if (!value.includes("://")) {
    value = `http://${value}`;
  }

  try {
    const parsed = new URL(value);
    if (!parsed.port && parsed.hostname.endsWith(".railway.internal")) {
      parsed.port = String(defaultInternalPort);
    }
    return parsed.toString().replace(/\/$/, "");
  } catch (_err) {
    return fallback;
  }
}

function normalizePhoneToJid(phone) {
  if (typeof phone !== "string") return "";
  const raw = phone.trim();
  if (!raw) return "";
  if (raw.includes("@")) return raw;

  const digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  return `${digits}@s.whatsapp.net`;
}

async function withTimeout(promise, timeoutMs) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`send timed out after ${timeoutMs}ms`)), timeoutMs);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

const FASTAPI_URL = normalizeServiceUrl(
  process.env.FASTAPI_URL,
  "http://localhost:8000",
  8080,
);
const PORT = parseInt(process.env.PORT, 10) || 3000;
const OUTBOUND_ONLY = (process.env.WA_OUTBOUND_ONLY ?? "true").toLowerCase() === "true";
const SEND_TIMEOUT_MS = parseInt(process.env.WA_SEND_TIMEOUT_MS || "20000", 10);
const QUEUE_MAX_SIZE = parseInt(process.env.WA_QUEUE_MAX_SIZE || "500", 10);
const QUEUE_MAX_ATTEMPTS = parseInt(process.env.WA_QUEUE_MAX_ATTEMPTS || "12", 10);
const QUEUE_RETRY_DELAY_MS = parseInt(process.env.WA_QUEUE_RETRY_DELAY_MS || "10000", 10);
const QUEUE_FLUSH_INTERVAL_MS = parseInt(process.env.WA_QUEUE_FLUSH_INTERVAL_MS || "5000", 10);

const logger = pino({ level: "warn" });

let sock = null;
let connectionStatus = "disconnected";
const botSentIds = new Set(); // track messages sent by the bot to avoid loops
const outboundQueue = [];
let flushInProgress = false;

function enqueueMessage(jid, message, reason) {
  if (outboundQueue.length >= QUEUE_MAX_SIZE) {
    return { ok: false, reason: "queue_full" };
  }
  outboundQueue.push({
    jid,
    message,
    attempts: 0,
    nextAttemptAt: Date.now(),
    lastError: reason || null,
  });
  return { ok: true };
}

async function sendViaSocket(jid, message) {
  if (connectionStatus !== "connected" || !sock) {
    throw new Error("WhatsApp not connected");
  }
  await withTimeout(sock.sendMessage(jid, { text: message }), SEND_TIMEOUT_MS);
}

async function flushQueue() {
  if (flushInProgress) return;
  if (connectionStatus !== "connected" || !sock) return;
  if (outboundQueue.length === 0) return;

  flushInProgress = true;
  try {
    const now = Date.now();
    for (let i = 0; i < outboundQueue.length; i += 1) {
      const item = outboundQueue[i];
      if (item.nextAttemptAt > now) continue;

      try {
        await sendViaSocket(item.jid, item.message);
        outboundQueue.splice(i, 1);
        i -= 1;
      } catch (err) {
        item.attempts += 1;
        item.lastError = err?.message || "Unknown error";
        item.nextAttemptAt = Date.now() + QUEUE_RETRY_DELAY_MS;
        if (item.attempts >= QUEUE_MAX_ATTEMPTS) {
          console.error(`Dropping queued message after ${item.attempts} attempts: ${item.lastError}`);
          outboundQueue.splice(i, 1);
          i -= 1;
        }
      }
    }
  } finally {
    flushInProgress = false;
  }
}

// ── WhatsApp connection ────────────────────────────────────────────

async function startWhatsApp() {
  // Ensure auth_info directory exists
  const authDir = process.env.RAILWAY_VOLUME_MOUNT_PATH
    ? path.join(process.env.RAILWAY_VOLUME_MOUNT_PATH, "auth_info")
    : path.join(__dirname, "auth_info");
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  const { state, saveCreds } = await useMultiFileAuthState(authDir);

  sock = makeWASocket({
    auth: state,
    logger,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("Scan this QR code with WhatsApp:");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      connectionStatus = "connected";
      console.log("WhatsApp connected");
      flushQueue().catch((err) => {
        console.error("Queue flush failed:", err?.message || err);
      });
    }

    if (connection === "close") {
      connectionStatus = "disconnected";
      const statusCode =
        lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      console.log(
        `Connection closed (status ${statusCode}). ${shouldReconnect ? "Reconnecting..." : "Logged out — not reconnecting."}`
      );

      if (shouldReconnect) {
        setTimeout(() => startWhatsApp(), 3000); // Wait 3s before retry
      }
    }
  });

  // ── Incoming messages → forward to FastAPI ───────────────────────

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    if (OUTBOUND_ONLY) return;

    for (const msg of messages) {
      // Skip messages the bot itself sent (prevents reply loops)
      if (botSentIds.has(msg.key.id)) {
        botSentIds.delete(msg.key.id);
        continue;
      }

      const text =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text;
      if (!text) continue;

      const jid = msg.key.remoteJid;
      if (jid.endsWith("@lid")) continue;
      const phone = jid.replace(/@s\.whatsapp\.net$/, "");

      try {
        const res = await fetch(`${FASTAPI_URL}/api/wa/incoming`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, message: text }),
        });
        if (!res.ok) {
          console.error(`FastAPI responded ${res.status}`);
        } else {
          const data = await res.json();
          if (data.reply) {
            const sent = await sock.sendMessage(msg.key.remoteJid, { text: data.reply });
            if (sent?.key?.id) botSentIds.add(sent.key.id);
          }
        }
      } catch (err) {
        console.error("Failed to forward message to FastAPI:", err.message);
      }
    }
  });
}

// ── HTTP API ───────────────────────────────────────────────────────

const app = express();
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({
    status: connectionStatus,
    queued: outboundQueue.length,
  });
});

app.post("/send", async (req, res) => {
  const { phone, message } = req.body || {};

  if (!phone || !message) {
    return res.status(400).json({ error: "phone and message are required" });
  }

  const jid = normalizePhoneToJid(phone);
  if (!jid) {
    return res.status(400).json({ error: "Invalid phone format" });
  }

  if (connectionStatus !== "connected" || !sock) {
    const queued = enqueueMessage(jid, message, "WhatsApp not connected");
    if (!queued.ok) {
      return res.status(503).json({ error: "WhatsApp not connected and queue is full" });
    }
    return res.status(202).json({ ok: true, queued: true });
  }

  try {
    await sendViaSocket(jid, message);
    res.json({ ok: true, queued: false });
  } catch (err) {
    const errMsg = err?.message || "Unknown error";
    const queued = enqueueMessage(jid, message, errMsg);
    if (!queued.ok) {
      console.error("Send failed and queue full:", errMsg);
      return res.status(502).json({ error: `Failed to send message and queue is full: ${errMsg}` });
    }
    console.error("Send failed, queued for retry:", errMsg);
    res.status(202).json({ ok: true, queued: true, error: errMsg });
  }
});

// ── Start ──────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`wa-bridge HTTP listening on port ${PORT}`);
});

setInterval(() => {
  flushQueue().catch((err) => {
    console.error("Periodic queue flush failed:", err?.message || err);
  });
}, QUEUE_FLUSH_INTERVAL_MS);

startWhatsApp().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
