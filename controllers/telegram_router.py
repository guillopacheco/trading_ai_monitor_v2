"""
controllers/telegram_router.py
------------------------------
Router de mensajes entrantes de Telegram.

Decide:
    - Si el texto es un comando → commands_controller.execute_command
    - Si es una posible señal → signal_controller.process_new_signal
"""

import logging
from utils.helpers import is_command, extract_command
from controllers.commands_controller import execute_command
from controllers.signal_controller import process_new_signal

logger = logging.getLogger("telegram_router")


async def route_incoming_message(raw_text: str) -> None:
    """
    Punto de entrada único para mensajes de Telegram.
    """
    text = (raw_text or "").strip()
    if not text:
        return

    if is_command(text):
        cmd, args = extract_command(text)
        logger.info(f"📥 Comando recibido: {cmd} {args}")
        await execute_command(cmd, args)
    else:
        logger.info("📥 Posible señal recibida desde canal VIP.")
        await process_new_signal(text)
