"""
controllers/positions_controller.py
-----------------------------------
Monitorea posiciones abiertas:
  ✔ obtención desde Bybit
  ✔ análisis de reversión con motor técnico
  ✔ sugerencias de cerrar, mantener, revertir
"""

import logging
from core.signal_engine import analyze_reversal
from services.bybit_service import get_open_positions
from services.telegram_service import send_message

logger = logging.getLogger("positions_controller")


async def check_positions():
    """
    Llamado periódicamente por scheduler_service.
    """
    positions = get_open_positions()
    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for p in positions:
        symbol = p["symbol"]
        direction = p["side"].lower()  # long/short

        logger.info(f"🔍 Analizando posición abierta: {symbol} ({direction})")

        reversal = analyze_reversal(symbol, direction)
        if reversal.get("reversal"):
            await send_message(
                f"🚨 Reversión detectada en {symbol}\n"
                f"Motivo: {reversal['reason']}"
            )
        else:
            logger.info(f"✔ Sin reversión para {symbol}")
