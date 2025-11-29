"""
controllers/signal_listener.py
-------------------------------
Recibe señales del router y delega el procesado al signal_controller.
"""

import logging
from controllers.signal_controller import process_new_signal

logger = logging.getLogger("signal_listener")


def on_new_signal(raw_text: str):
    """Llamado por telegram_router cuando llega un texto del canal VIP."""
    logger.info("📩 Señal detectada por listener.")
    process_new_signal(raw_text)
