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
    logger.info(f"📥 Recibida señal nueva: {symbol} ({direction}) entry={entry_price}")

    # 1) Guardar señal
    db_insert_signal(symbol, direction, entry_price)

    # 2) Analizar señal
    result = await analyze_symbol(symbol, direction)

    # 3) Formatear mensaje
    msg = format_analysis_for_telegram(result)

    logger.info(f"📤 Resultado enviado para señal nueva: {symbol}")
    return msg


# ============================================================
# ♻️ EVALUAR SEÑALES PENDIENTES
# ============================================================

async def evaluate_pending_signal(signal_row: dict) -> tuple[str, str]:
    symbol = signal_row["symbol"]
    direction = signal_row["direction"]

    logger.info(f"♻️ Evaluando señal pendiente: {symbol} ({direction})")
    result = await analyze_symbol(symbol, direction)

    decision = result.decision

    if decision.get("decision") == "reactivate":
        db_update_signal_status(symbol, "reactivated")
        msg = f"🟢 Señal REACTIVADA: {symbol} ({direction})\n\n" + format_analysis_for_telegram(result)
        return symbol, msg

    msg = f"⏳ Señal aún NO lista para reactivar: {symbol}\n" + \
          f"Motivo: {decision.get('decision_reasons', ['N/A'])[0]}"
    return symbol, msg


async def evaluate_all_pending_signals() -> list[tuple[str, str]]:
    pending = db_get_pending_signals()
    results = []
    for s in pending:
        symbol, msg = await evaluate_pending_signal(s)
        results.append((symbol, msg))
    return results


# ============================================================
# 🟦 SERVICE WRAPPER (para coordinadores)
# ============================================================

class SignalService:

    async def process_new(self, symbol: str, direction: str, entry_price=None):
        return await process_new_signal(symbol, direction, entry_price)

    async def evaluate_pending(self, signal_row: dict):
        return await evaluate_pending_signal(signal_row)

    async def evaluate_all_pending(self):
        return await evaluate_all_pending_signals()
