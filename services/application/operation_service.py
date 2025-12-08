# services/application/operation_service.py

import logging
from datetime import datetime

from services.application.analysis_service import analyze_symbol, format_analysis_for_telegram
from services.bybit.bybit_private import get_open_positions
from services.bybit.bybit_private import reverse_position, close_position

logger = logging.getLogger("operation_service")


class OperationDTO:
    """Objeto limpio para transportar datos de una operación abierta."""
    def __init__(self, symbol, direction, entry_price, current_price, pnl_pct):
        self.symbol = symbol
        self.direction = direction  # long | short
        self.entry_price = entry_price
        self.current_price = current_price
        self.pnl_pct = pnl_pct      # % ganancia/pérdida


# ============================================================
# 🔍 CARGAR OPERACIONES ABIERTAS DESDE BYBIT
# ============================================================

async def load_open_operations() -> list[OperationDTO]:
    """
    Obtiene todas las operaciones abiertas en Bybit (API privada).
    Convierte a DTO interno estandarizado.
    """

    raw_positions = await get_open_positions()
    operations = []

    for pos in raw_positions:
        try:
            op = OperationDTO(
                symbol=pos["symbol"],
                direction=pos["direction"],
                entry_price=float(pos["entry_price"]),
                current_price=float(pos["mark_price"]),
                pnl_pct=float(pos["pnl_pct"])
            )
            operations.append(op)
        except Exception:
            logger.exception("❌ Error procesando posición BYBIT")

    return operations


# ============================================================
# 🔥 EVALUAR SI UNA OPERACIÓN NECESITA ACCIÓN URGENTE
# ============================================================

def classify_risk(pnl_pct: float) -> tuple[str, str]:
    """
    Clasificación lógica de riesgo según % de pérdida o ganancia.
    Devuelve: (riesgo, texto)
    """

    if pnl_pct <= -90:
        return "critical", "⚠️ Pérdida extrema (-90%) — Acción inmediata recomendada."
    elif pnl_pct <= -70:
        return "very_high", "⚠️ Riesgo MUY alto (-70%) — Revisión urgente."
    elif pnl_pct <= -50:
        return "high", "⚠️ Pérdida alta (-50%) — Evaluar reversión/ cierre."
    elif pnl_pct <= -30:
        return "medium", "⚠️ Pérdida moderada (-30%) — Revisar condiciones."
    else:
        return "safe", "Operación estable."


# ============================================================
# 🔎 EVALUACIÓN COMPLETA DE UNA OPERACIÓN ABIERTA
# ============================================================

async def evaluate_single_operation(op: OperationDTO) -> str:
    """
    Analiza una sola operación y devuelve mensaje formateado para Telegram.
    """

    logger.info(f"📉 Evaluando operación abierta: {op.symbol} ({op.direction})")

    # 1) Clasificación de riesgo basada en % de pérdida
    risk_level, risk_msg = classify_risk(op.pnl_pct)

    # 2) Pedir al motor técnico el análisis de contexto
    tech = await analyze_symbol(op.symbol, op.direction)

    decision = tech.decision
    snapshot = tech.snapshot

    # ======================================
    # 🔥 DECISIÓN BASADA EN MOTOR + PÉRDIDA
    # ======================================

    if risk_level in ["critical", "very_high"]:
        final = "close"
        note = "Pérdida severa — no es recuperable según tendencia."
    elif risk_level == "high":
        # Revisar si la tendencia está completamente en contra
        if decision["major_trend_code"] == ("bear" if op.direction == "long" else "bull"):
            final = "reverse"
            note = "Tendencia completamente en contra — revertir posición."
        else:
            final = "close"
            note = "Pérdida alta pero tendencia no completamente opuesta."
    elif risk_level == "medium":
        final = "evaluate"
        note = "Monitoreo recomendado — condiciones mixtas."
    else:
        final = "hold"
        note = "Operación sana — mantener."

    # ======================================
    # 📝 MENSAJE FORMATEADO PARA TELEGRAM
    # ======================================

    msg = f"""
📌 *Evaluación de operación abierta*

🔹 *Par:* {op.symbol}
🔹 *Dirección:* {op.direction}
🔹 *Entrada:* {op.entry_price}
🔹 *Precio actual:* {op.current_price}
🔹 *PnL:* {op.pnl_pct:.2f}%

📊 *Riesgo:* {risk_level.upper()}
{risk_msg}

📘 *Análisis técnico actual:*
{format_analysis_for_telegram(tech)}

🎯 *Recomendación final:* {final.upper()}
➡️ {note}
"""

    return msg


# ============================================================
# 🔁 EVALUAR TODAS LAS OPERACIONES ABIERTAS
# ============================================================

async def evaluate_all_operations() -> list[str]:
    """
    Evalúa todas las operaciones en Bybit y retorna mensajes para Telegram.
    """

    ops = await load_open_operations()
    results = []

    for op in ops:
        msg = await evaluate_single_operation(op)
        results.append(msg)

    return results


# ============================================================
# 🔄 EJECUTAR REVERSION / CIERRE (OPCIONAL)
# ============================================================

async def apply_action(op: OperationDTO, action: str) -> str:
    """
    Aplica acción real en Bybit: close | reverse
    """

    if action == "close":
        await close_position(op.symbol)
        return f"🛑 Operación cerrada: {op.symbol}"

    elif action == "reverse":
        await reverse_position(op.symbol)
        return f"🔄 Operación revertida: {op.symbol}"

    else:
        return "❓ Acción no reconocida."
