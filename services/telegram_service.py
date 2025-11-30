"""
services/telegram_service.py
----------------------------
Servicio encargado de manejar la conexión con Telegram.

Este módulo NO importa controllers.
Únicamente crea el cliente de Telethon, lo inicializa
y expone una función send_message() para que los controllers
puedan enviar mensajes sin generar ciclos.
"""

import logging
from telethon import TelegramClient
from telethon import events
from controllers.telegram_router import route_incoming_message
from config import (
    API_ID,
    API_HASH,
    TELEGRAM_SESSION,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_ID,
)

logger = logging.getLogger("telegram_service")

# ============================================================
# 🔵 Cliente Global de Telegram
# ============================================================

client = TelegramClient(
    TELEGRAM_SESSION,
    API_ID,
    API_HASH
)

# ============================================================
# 🛡 send seguro — evita errores en otros módulos
# ============================================================
async def safe_send(text: str):
    """Enviar mensaje usando el BOT de forma segura, sin romper el flujo."""
    try:
        await client.send_message(TELEGRAM_USER_ID, text)
    except Exception as e:
        log.error(f"❌ Error enviando mensaje seguro: {e}")

# ============================================================
# 🔵 Inicialización de Telegram (usuario + bot)
# ============================================================

async def start_telegram():
    """
    Inicia sesión del cliente de usuario y del bot.
    NO registra eventos; eso se hace en controllers/telegram_router.py.
    """
    try:
        await client.connect()

        # Sesión de usuario
        if not await client.is_user_authorized():
            logger.warning("⚠️ La sesión de usuario no está autorizada.")
            # Aquí normalmente se pediría código, pero lo omitimos.

        # Iniciar el bot
        await client.start(bot_token=TELEGRAM_BOT_TOKEN)

        logger.info("📡 Telegram conectado (usuario + bot).")

    except Exception as e:
        logger.error(f"❌ Error inicializando Telegram: {e}")
        raise


# ============================================================
# 🔵 Enviar mensaje
# ============================================================

async def send_message(text: str, chat_id: int = None):
    """
    Envia un mensaje por Telegram.
    Si no se indica chat_id, se envía al usuario dueño (TELEGRAM_USER_ID).
    """
    try:
        if chat_id is None:
            chat_id = TELEGRAM_USER_ID

        await client.send_message(chat_id, text)

    except Exception as e:
        logger.error(f"❌ Error enviando mensaje Telegram: {e}")

# ============================================================
# 🔵 Captura de mensajes entrantes
# ============================================================

@client.on(events.NewMessage())
async def _handle_incoming_message(event):
    """
    Captura cualquier mensaje recibido (canal VIP + usuario).
    Los envía al router principal.
    """
    try:
        raw_text = event.raw_text.strip()
        if not raw_text:
            return

        # Enviar al router
        await route_incoming_message(raw_text)

    except Exception as e:
        logger.error(f"❌ Error manejando mensaje entrante: {e}")
