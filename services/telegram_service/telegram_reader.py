# services/telegram_service/telegram_reader.py
import asyncio
import logging
from telethon import TelegramClient, events
from config import API_ID, API_HASH, TELEGRAM_SESSION, TELEGRAM_VIP_CHANNEL_ID

logger = logging.getLogger("telegram_reader")


async def start_telegram_reader(app_layer):
    """
    Inicia Telethon y escucha señales del canal.
    """
    if not (API_ID and API_HASH and TELEGRAM_VIP_CHANNEL_ID):
        logger.error(
            "❌ Telethon no puede iniciar: faltan API_ID/API_HASH/TELEGRAM_VIP_CHANNEL_ID en config/.env"
        )
        return

    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)
    await client.start()

    logger.info("📡 Cliente Telethon conectado y listo para escuchar señales...")
    logger.info("📡 Escuchando canal VIP...")

    @client.on(events.NewMessage(chats=TELEGRAM_VIP_CHANNEL_ID))
    async def handler(event):
        text = event.message.message or ""
        # Aquí enlazas tu parser / save_signal / analyze, etc.
        logger.info(f"📩 Señal recibida: {text[:120]}")

        signal = parse_signal(event.message.text)
        if not signal:
            return

        signal_id = app_layer.signal_service.register_signal(
            symbol=signal["symbol"],
            direction=signal["direction"],
            raw_text=event.message.text,
        )

        if not signal_id:
            return

        await app_layer.signal.handle_new_signal(
            {
                "id": signal_id,
                "symbol": signal["symbol"],
                "direction": signal["direction"],
            }
        )

    await client.run_until_disconnected()
