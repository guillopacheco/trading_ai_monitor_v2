"""
controllers/signal_listener.py
------------------------------
Escucha señales entrantes desde Telegram (canal VIP).
"""

import logging
from controllers.signal_controller import process_new_signal

logger = logging.getLogger("signal_listener")


async def on_new_signal(event):
    """
    Recibe mensaje del canal VIP → pasa al signal_controller.
    """
    try:
        text = event.raw_text
        logger.info(f"📩 Señal recibida desde canal VIP.")

        await process_new_signal(text)

    except Exception as e:
        logger.error(f"❌ Error procesando señal desde Telegram: {e}")
