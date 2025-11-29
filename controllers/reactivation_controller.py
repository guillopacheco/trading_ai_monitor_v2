"""
controllers/reactivation_controller.py
--------------------------------------
Procesa las señales en estado "pending" y decide si reactivarlas.
"""

import logging
from core.signal_engine import analyze_reactivation
from services import db_service
from services.telegram_service import send_message

logger = logging.getLogger("reactivation_controller")


def check_pending_signals():
    """Revisa todas las señales pendientes y decide si reactivarlas."""
    pending = db_service.get_pending_signals()

    if not pending:
        logger.info("📭 No hay señales pendientes para reactivar.")
        return

    for sig in pending:
        logger.info(f"♻️ Evaluando reactivación: {sig.symbol} ({sig.direction})")

        result = analyze_reactivation(sig)

        if not result["analysis"]["allowed"]:
            logger.info(f"⏳ {sig.symbol}: no apta para reactivación.")
            continue

        # Reactivada
        db_service.set_signal_status(sig.id, "reactivated")

        send_message(
            f"♻️ **Señal reactivada:** {sig.symbol}\n"
            f"→ {result['summary']}"
        )

        logger.info(f"✔ Señal reactivada: {sig.symbol}")
