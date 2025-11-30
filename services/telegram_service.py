"""
services/telegram_service.py
----------------------------
Capa central de comunicación con Telegram.

✅ Responsabilidades:
    - Crear y mantener el cliente de Telethon (usuario + bot)
    - Escuchar mensajes nuevos
    - Enviar mensajes al usuario (safe_send)
    - Despachar el texto entrante al router (telegram_router)

❌ NO debe importar controllers que a su vez lo importen a él.
"""

import logging
import asyncio
from telethon import TelegramClient, events

from config import (
    API_ID,
    API_HASH,
    TELEGRAM_SESSION,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_ID,
)

from controllers.telegram_router import route_incoming_message

logger = logging.getLogger("telegram_service")

# Cliente global (único)
client: TelegramClient | None = None


# ============================================================
# 📨 Enviar mensajes
# ============================================================

async def safe_send(text: str) -> None:
    """
    Envía un mensaje al usuario principal (TELEGRAM_USER_ID).
    Usa el cliente global ya conectado.
    """
    global client
    if client is None:
        logger.error("❌ safe_send llamado pero el cliente Telegram no está inicializado.")
        return
    try:
        await client.send_message(TELEGRAM_USER_ID, text)
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje a Telegram: {e}")


# ============================================================
# 📡 Inicialización y listeners
# ============================================================

async def start_telegram() -> TelegramClient:
    """
    Inicializa el cliente Telethon y registra el listener de mensajes.
    Devuelve el cliente para que main() pueda hacer run_until_disconnected().
    """
    global client

    logger.info("📡 Inicializando cliente de Telegram...")

    # Cliente "user+bot" con sesión compartida
    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)

    # Conectar usando bot_token (ya estás autenticado como usuario)
    await client.start(bot_token=TELEGRAM_BOT_TOKEN)

    logger.info("📡 Telegram conectado (usuario + bot).")

    # Listener de mensajes nuevos
    @client.on(events.NewMessage)
    async def _handler(event):
        text = (event.raw_text or "").strip()
        if not text:
            return
        try:
            await route_incoming_message(text)
        except Exception as e:
            logger.error(f"❌ Error en route_incoming_message: {e}")

    return client
    