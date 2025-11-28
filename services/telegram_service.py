"""
telegram_service.py
--------------------
Servicio oficial para manejar toda la interacción con Telegram usando Telethon.

Objetivos:
- Encapsular totalmente Telethon.
- Proveer una API limpia para envío de mensajes y escucha de señales/comandos.
- Evitar que la app dependa directamente de la lógica de Telethon.
- Reemplazar progresivamente telegram_reader.py y command_bot.py.

Componentes:
- send_message(text)
- start_signal_listener(callback)
- start_command_listener(callback)
"""

import asyncio
import logging
from telethon import TelegramClient, events

from config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_BOT_TOKEN,
    SIGNAL_CHANNEL_ID,
    USER_CHAT_ID,
)

logger = logging.getLogger("telegram_service")

# ============================================================
# 🔵 INICIALIZAR CLIENTE TELEGRAM
# ============================================================

# Cliente para el bot (comandos + envío)
bot_client = TelegramClient("bot_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

# Cliente para lectura de señales en canal VIP
signal_client = TelegramClient("signal_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)


# ============================================================
# 🔵 MÉTODO: ENVIAR MENSAJES
# ============================================================
async def send_message(text: str, chat_id: int = None):
    """
    Envía un mensaje usando el bot.
    """
    if chat_id is None:
        chat_id = USER_CHAT_ID  # por defecto, el canal privado del usuario

    try:
        await bot_client.send_message(chat_id, text)
        logger.info(f"📤 Mensaje enviado a {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")


# ============================================================
# 🔵 ESCUCHA DE SEÑALES VIP
# ============================================================
async def start_signal_listener(callback):
    """
    Escucha mensajes del canal VIP y entrega cada mensaje a `callback(message_text)`.

    callback: función async que recibe el texto y procesa la señal.
    """

    @signal_client.on(events.NewMessage(chats=SIGNAL_CHANNEL_ID))
    async def handler(event):
        try:
            text = event.raw_text
            logger.info(f"📥 Señal recibida del canal VIP:\n{text}")
            await callback(text)   # controlador de señales
        except Exception as e:
            logger.error(f"❌ Error procesando señal Telegram: {e}")

    logger.info("📡 Listener de señales iniciado.")
    await signal_client.start(bot_token=TELEGRAM_BOT_TOKEN)
    await signal_client.run_until_disconnected()


# ============================================================
# 🔵 ESCUCHA DE COMANDOS DEL BOT
# ============================================================
async def start_command_listener(callback):
    """
    Escucha comandos enviados al bot. Cada comando se entrega a `callback(command, params)`.

    callback: async, recibe (command: str, params: str)
    """

    @bot_client.on(events.NewMessage(pattern=r"^/"))
    async def handler(event):
        try:
            text = event.raw_text.strip()
            parts = text.split(" ", 1)

            command = parts[0]
            params = parts[1] if len(parts) > 1 else ""

            logger.info(f"🤖 Comando recibido: {command} {params}")
            await callback(command, params)
        except Exception as e:
            logger.error(f"❌ Error procesando comando: {e}")

    logger.info("🤖 Listener de comandos iniciado.")
    await bot_client.start(bot_token=TELEGRAM_BOT_TOKEN)
    await bot_client.run_until_disconnected()


# ============================================================
# 🔵 MODO INDIVIDUAL (TEST)
# ============================================================
if __name__ == "__main__":
    async def test():
        await bot_client.start(bot_token=TELEGRAM_BOT_TOKEN)
        await send_message("Telegram service funcionando correctamente.")

    asyncio.run(test())
