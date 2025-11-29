"""
services/telegram_service.py
----------------------------
Capa central de comunicación con Telegram.

✔ Cliente de usuario (Telethon) para:
    - Leer señales del canal VIP
    - Recibir comandos por chat privado
    - Enviar mensajes al usuario

No contiene lógica de análisis ni de DB.
"""

import logging
from telethon import TelegramClient, events

from config import (
    API_ID,
    API_HASH,
    TELEGRAM_SESSION,
    TELEGRAM_CHANNEL_ID,
    TELEGRAM_USER_ID,
)

from controllers.signal_listener import on_new_signal
from controllers.commands_controller import handle_command
from utils.helpers import is_command

logger = logging.getLogger("telegram_service")

# Cliente global de Telethon (sesión de usuario)
client = TelegramClient(
    TELEGRAM_SESSION,
    API_ID,
    API_HASH
)


async def send_message(text: str) -> bool:
    """
    Envía un mensaje al usuario configurado (TELEGRAM_USER_ID).
    """
    try:
        await client.send_message(TELEGRAM_USER_ID, text)
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje a Telegram: {e}")
        return False


@client.on(events.NewMessage)
async def handler(event):
    """
    Dispatcher general de mensajes:

    - Si viene del canal VIP → se trata como señal.
    - Si es un mensaje privado / comando → va a commands_controller.
    """
    try:
        chat_id = event.chat_id
        text = event.raw_text or ""

        # Señales del canal VIP
        if chat_id == TELEGRAM_CHANNEL_ID:
            logger.info("📥 Señal recibida desde canal VIP.")
            await on_new_signal(event)
            return

        # Comandos desde el chat privado
        if is_command(text):
            logger.info(f"💬 Comando recibido: {text}")
            await handle_command(text)
            return

    except Exception as e:
        logger.error(f"❌ Error en handler de Telegram: {e}")


async def start_telegram_service():
    """
    Inicializa el cliente de Telegram (sesión de usuario).
    """
    logger.info("📡 Iniciando servicio de Telegram (sesión de usuario)…")
    await client.start()  # Usa API_ID / API_HASH / TELEGRAM_SESSION
    me = await client.get_me()
    logger.info(f"🤖 Telegram conectado como: {me.username or me.id}")


def get_client() -> TelegramClient:
    """
    Devuelve el cliente Telethon para ser usado en main.py (run_until_disconnected).
    """
    return client
