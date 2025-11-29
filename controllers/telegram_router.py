"""
controllers/telegram_router.py
------------------------------
Enrutador de eventos de Telegram.

Este módulo SOLO conecta eventos entrantes con los controllers.
Importa el cliente desde telegram_service, y controllers para
procesar señales o comandos.

Evita ciclos de importación:
    - telegram_service NO importa controllers
    - controllers NO importan telegram_service para routing
"""

import logging
from telethon import events

from services.telegram_service import client
from controllers.signal_listener import on_new_signal
from controllers.commands_controller import handle_command
from utils.helpers import is_command
from config import TELEGRAM_CHANNEL_ID

logger = logging.getLogger("telegram_router")


# ============================================================
# 🔵 Handler de todos los mensajes entrantes
# ============================================================

@client.on(events.NewMessage)
async def router(event):
    """
    Redirige mensajes según origen:
    - Canal VIP → signal_listener
    - Mensajes de usuario que comienzan con / → commands_controller
    """
    try:
        text = event.raw_text or ""

        # Señales del canal VIP
        if event.chat_id == TELEGRAM_CHANNEL_ID:
            await on_new_signal(event)
            return

        # Comandos enviados por el usuario
        if is_command(text):
            await handle_command(text)
            return

    except Exception as e:
        logger.error(f"❌ Error en telegram_router: {e}")
