from services.telegram_sender import send
from core.signal_engine import analyze_signal
from services.db_service import save_new_signal, add_analysis_log
import logging

logger = logging.getLogger("signal_controller")


async def process_new_signal(raw_text):
    """Analiza una señal y envía recomendación."""
    parsed = analyze_signal(raw_text)

    save_new_signal(parsed)
    add_analysis_log(parsed)

    await send(parsed["summary"])
