import makeWASocket, { useMultiFileAuthState, DisconnectReason } from "@whiskeysockets/baileys";
import pino from "pino";
import express from "express";
import qrcode from "qrcode-terminal";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000";
const PORT = parseInt(process.env.PORT, 10) || 3000;
const OUTBOUND_ONLY = (process.env.WA_OUTBOUND_ONLY ?? "true").toLowerCase() === "true";

const logger = pino({ level: "warn" });

let sock = null;
let connectionStatus = "disconnected";
const botSentIds = new Set(); // track messages sent by the bot to avoid loops

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
  res.json({ status: connectionStatus });
});

app.post("/send", async (req, res) => {
  const { phone, message } = req.body || {};

  if (!phone || !message) {
    return res.status(400).json({ error: "phone and message are required" });
  }

  if (connectionStatus !== "connected" || !sock) {
    return res.status(503).json({ error: "WhatsApp not connected" });
  }

  const jid = phone.includes("@") ? phone : `${phone}@s.whatsapp.net`;

  try {
    await sock.sendMessage(jid, { text: message });
    res.json({ ok: true });
  } catch (err) {
    console.error("Send failed:", err.message);
    res.status(500).json({ error: "Failed to send message" });
  }
});

// ── Start ──────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`wa-bridge HTTP listening on port ${PORT}`);
});

startWhatsApp().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
