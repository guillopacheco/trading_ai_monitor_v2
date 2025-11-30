import logging
from telethon import TelegramClient, events
from config import (
    API_ID,
    API_HASH,
    TELEGRAM_SESSION,
    TELEGRAM_CHANNEL_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_ID,
)

from controllers.telegram_router import route_incoming_message

logger = logging.getLogger("telegram_service")

client = TelegramClient(
    TELEGRAM_SESSION,
    API_ID,
    API_HASH,
)

async def start_telegram():
    """Inicia conexión Telegram."""
    await client.start(bot_token=TELEGRAM_BOT_TOKEN)
    logger.info("📡 Telegram conectado (usuario + bot).")

    @client.on(events.NewMessage)
    async def handle_message(event):
        raw = event.raw_text
        await route_incoming_message(raw)

