"""
controllers/reactivation_controller.py
--------------------------------------
Ejecuta reactivaciones periódicas:
  ✔ obtener señales pendientes
  ✔ analizar con el motor
  ✔ reactivar si match_ratio >= 70
"""

import logging
from core.signal_engine import analyze_reactivation
from services import db_service
from services.telegram_service import send_message

logger = logging.getLogger("reactivation_controller")


async def run_reactivation_cycle():
    """
    Se ejecuta desde scheduler_service cada X minutos.
    """
    signals = db_service.get_pending_signals()
    if not signals:
        logger.info("📭 No hay señales pendientes para reactivar.")
        return

    logger.info(f"♻️ Revisando {len(signals)} señales pendientes...")

    for raw in signals:
        try:
            from models.signal import Signal
            signal = Signal(**raw)

            logger.info(f"♻️ Revisando {signal.symbol} ({signal.direction})")

            result = analyze_reactivation(signal)

            if result.get("reactivated"):
                db_service.set_signal_reactivated(signal.id)
                await send_message(f"🔄 Señal {signal.symbol} reactivada ✔")
            else:
                logger.info(f"⏳ Señal {signal.symbol} NO reactivada")

        except Exception as e:
            logger.error(f"❌ Error en revisión de {raw.get('symbol')}: {e}")
