# services/application/signal_service.py

import logging
from datetime import datetime

from database import db_insert_signal, db_update_signal_status, db_get_pending_signals
from services.application.analysis_service import analyze_symbol, format_analysis_for_telegram

logger = logging.getLogger("signal_service")


class SignalDTO:
    """DTO estandarizado de una señal."""
    def __init__(self, symbol, direction, entry=None, timestamp=None, status="pending"):
        self.symbol = symbol
        self.direction = direction
        self.entry = entry
        self.timestamp = timestamp or datetime.utcnow()
        self.status = status


# ============================================================
# 📌 PROCESAR SEÑAL NUEVA DEL CANAL VIP
# ============================================================

async def process_new_signal(symbol: str, direction: str, entry_price: float | None = None) -> str:
    """
    Guarda una señal nueva en la DB y la analiza inmediatamente.
    Devuelve mensaje formateado para Telegram.
    """

    logger.info(f"📥 Recibida señal nueva: {symbol} ({direction}) entry={entry_price}")

    # 1) Guardar en la DB
    db_insert_signal(symbol, direction, entry_price)

    # 2) Ejecutar análisis técnico
    result = await analyze_symbol(symbol, direction)

    # 3) Preparar mensaje final
    msg = format_analysis_for_telegram(result)

    logger.info(f"📤 Resultado enviado para señal nueva: {symbol}")

    return msg


# ============================================================
# ♻️ PROCESAR SEÑALES PENDIENTES (REACTIVACIÓN)
# ============================================================

async def evaluate_pending_signal(signal_row: dict) -> tuple[str, str]:
    """
    Evalúa una señal pendiente desde la DB.
    Retorna: (symbol, mensaje)
    """

    symbol = signal_row["symbol"]
    direction = signal_row["direction"]

    logger.info(f"♻️ Evaluando señal pendiente: {symbol} ({direction})")

    # 1) Ejecutar análisis con el motor técnico
    result = await analyze_symbol(symbol, direction)
    decision = result.decision

    # 2) Determinar si debe reactivarse o seguir pendiente
    if decision.get("decision") == "reactivate":
        db_update_signal_status(symbol, "reactivated")

        logger.info(f"🔄 Señal {symbol} reactivada")

        msg = f"🟢 Señal REACTIVADA: {symbol} ({direction})\n\n" + \
              format_analysis_for_telegram(result)

        return symbol, msg

    else:
        logger.info(f"⏳ Señal {symbol} sigue pendiente")

        msg = f"⏳ Señal aún NO lista para reactivar: {symbol}\n" + \
              f"Motivo: {decision.get('decision_reasons', ['N/A'])[0]}"

        return symbol, msg


async def evaluate_all_pending_signals() -> list[tuple[str, str]]:
    """
    Evalúa todas las señales en estado 'pending' en la DB.
    Retorna una lista de (symbol, mensaje).
    """

    pending = db_get_pending_signals()
    results = []

    for s in pending:
        symbol, msg = await evaluate_pending_signal(s)
        results.append((symbol, msg))

    return results
