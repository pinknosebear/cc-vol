const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys");
const pino = require("pino");
const express = require("express");
const qrcode = require("qrcode-terminal");

const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000";
const PORT = parseInt(process.env.PORT, 10) || 3000;

const logger = pino({ level: "warn" });

let sock = null;
let connectionStatus = "disconnected";

// ── WhatsApp connection ────────────────────────────────────────────

async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("auth_info");

  sock = makeWASocket({
    auth: state,
    logger,
    printQRInTerminal: false, // we handle QR ourselves
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
        startWhatsApp();
      }
    }
  });

  // ── Incoming messages → forward to FastAPI ───────────────────────

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;

    for (const msg of messages) {
      // Only forward text messages, skip our own outgoing messages
      if (msg.key.fromMe) continue;
      const text =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text;
      if (!text) continue;

      const phone = msg.key.remoteJid.replace("@s.whatsapp.net", "");

      try {
        const res = await fetch(`${FASTAPI_URL}/api/wa/incoming`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, message: text }),
        });
        if (!res.ok) {
          console.error(`FastAPI responded ${res.status}`);
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
