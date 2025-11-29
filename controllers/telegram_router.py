"""
controllers/telegram_router.py
-------------------------------
Recibe mensajes desde telegram_service y los enruta correctamente.
"""

import logging
from utils.helpers import is_command
from controllers.signal_listener import on_new_signal
from controllers.commands_controller import execute_command

logger = logging.getLogger("telegram_router")


def route_incoming_message(raw_text: str):
    """Determina si el mensaje es comando o señal normal."""

    if is_command(raw_text):
        execute_command(raw_text)
        return

    # Sino, es señal
    on_new_signal(raw_text)
