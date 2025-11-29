"""
controllers/positions_controller.py
-----------------------------------
Analiza posiciones reales y detecta reversiones / decisiones.
"""

import logging
from core.signal_engine import analyze_open_position
from services.bybit_service import get_open_positions
from services.telegram_service import send_message

logger = logging.getLogger("positions_controller")


def check_open_positions():
    """Recorre todas las posiciones abiertas y ejecuta el motor técnico."""
    positions = get_open_positions()

    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for p in positions:
        logger.info(f"🔍 Analizando posición: {p['symbol']} ({p['side']})")

        result = analyze_open_position(
            symbol=p["symbol"],
            direction=p["side"],
        )

        send_message(
            f"🔍 **Análisis de posición:** {p['symbol']}\n"
            f"{result['summary']}"
        )
