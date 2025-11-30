# services/telegram_sender.py
import logging
from config import TELEGRAM_USER_ID
from services.telegram_service import client

logger = logging.getLogger("telegram_sender")


async def send(text: str, chat_id: int = None):
    """Envía mensaje sin generar imports circulares."""
    try:
        if chat_id is None:
            chat_id = TELEGRAM_USER_ID

        await client.send_message(chat_id, text)

    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")


async def safe_send(text: str, chat_id: int = None):
    """Versión segura con manejo silencioso de errores."""
    try:
        if chat_id is None:
            chat_id = TELEGRAM_USER_ID

        await client.send_message(chat_id, text)
    except Exception:
        pass
