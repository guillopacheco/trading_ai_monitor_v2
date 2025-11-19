"""
operation_tracker.py — versión final unificada con technical_brain
-------------------------------------------------------------------
Monitor inteligente de operaciones abiertas en Bybit.

Funciones:
✔ Usa analyze_market() para obtener tendencias multi-TF
✔ Detecta pérdidas críticas por niveles
✔ Calcula ROI real y PnL
✔ Genera recomendación inteligente
✔ Envía alerta mediante notifier.notify_operation_alert()
"""

import logging
from typing import Dict, Any

from bybit_client import get_open_positions
from notifier import notify_operation_alert
from technical_brain import analyze_market

logger = logging.getLogger("operation_tracker")

# ============================================================
# 🔢 Cálculo ROI y niveles de pérdida
# ============================================================

LOSS_LEVELS = [-3, -5, -10, -20, -30, -50, -70]


def compute_roi(entry: float, mark: float, leverage: int, direction: str) -> float:
    if entry <= 0:
        return 0.0

    roi = ((mark - entry) / entry) * 100
    if direction == "short":
        roi *= -1

    return roi * leverage


def compute_loss_level(roi: float) -> int | None:
    for lvl in LOSS_LEVELS:
        if roi <= lvl:
            return lvl
    return None


# ============================================================
# 🧠 Recomendación inteligente
# ============================================================

def build_suggestion(direction: str, analysis: Dict[str, Any], roi: float) -> str:
    """
    Usa analyze_market() para decidir la recomendación:
    - Cerrar
    - Revertir
    - Mantener
    """

    global_trend = analysis.get("overall_trend", "neutral")
    entry_ok = analysis.get("entry_ok", False)

    # Fuerte pérdida → decisiones duras
    if roi <= -20:
        if (direction == "long" and global_trend == "bearish") or \
           (direction == "short" and global_trend == "bullish"):
            return "Cerrar o revertir inmediatamente (tendencia muy desfavorable)"

    # Tendencia opuesta
    if (direction == "long" and global_trend == "bearish") or \
       (direction == "short" and global_trend == "bullish"):
        return "Tendencia desfavorable: evaluar cierre"

    if entry_ok and roi > 0:
        return "Operación saludable, mantener"

    if abs(roi) < 5:
        return "Movimiento neutro, continuar monitoreando"

    return "Evaluación estándar"


# ============================================================
# 🚨 Monitor principal
# ============================================================

def monitor_open_positions():
    logger.info("📡 Iniciando evaluación de operaciones activas...")

    positions = get_open_positions()
    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for pos in positions:
        try:
            symbol = pos.get("symbol", "").upper()
            side = (pos.get("side") or "").lower()
            direction = "long" if side == "buy" else "short"

            entry = float(pos.get("entryPrice") or 0)
            mark = float(pos.get("markPrice") or entry)
            pnl = float(pos.get("unrealisedPnl") or 0)
            lev = int(float(pos.get("leverage") or 20))

            if entry <= 0:
                logger.warning(f"⚠️ Entrada inválida para posición: {pos}")
                continue

            roi = compute_roi(entry, mark, lev, direction)
            loss_level = compute_loss_level(roi)

            logger.info(
                f"🔎 {symbol} | {direction.upper()} x{lev} | ROI={roi:.2f}% | Entry={entry} Mark={mark}"
            )

            if loss_level is None:
                continue  # operación saludable

            # Obtener análisis unificado
            analysis = analyze_market(symbol, direction_hint=direction)

            # Recomendación final
            suggestion = build_suggestion(direction, analysis, roi)

            # Enviar alerta
            notify_operation_alert(
                symbol=symbol,
                direction=direction,
                roi=roi,
                pnl=pnl,
                loss_level=loss_level,
                volatility=analysis.get("overall_trend", "N/A"),
                suggestion=suggestion
            )

        except Exception as e:
            logger.error(f"❌ Error evaluando operación {pos}: {e}")
