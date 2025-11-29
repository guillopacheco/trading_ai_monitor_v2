# services/telegram_bridge.py
"""
Bridge seguro para enviar mensajes a Telegram sin generar ciclos de importación.
"""

import logging

logger = logging.getLogger("telegram_bridge")

def safe_send(text: str):
    """
    Import diferido para evitar ciclos. Telegram sólo se importa al ejecutarse.
    """
    try:
        from services.telegram_service import send_message
        send_message(text)
    except Exception as e:
        logger.error(f"❌ Error en safe_send: {e}")
