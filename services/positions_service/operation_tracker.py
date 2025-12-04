import logging
import asyncio
from typing import Dict, Any

from config import SIMULATION_MODE
from services.technical_engine.trend_system_final import analyze_trend_core
from services.bybit_service.bybit_client import get_open_positions
from services.telegram_service.notifier import send_message, notify_operation_recommendation

from core.helpers import (
    calculate_roi,
    calculate_loss_pct_from_roi,
    calculate_pnl,
)

logger = logging.getLogger("operation_tracker")

LOSS_LEVELS = [-20, -30, -50, -70]


def compute_loss_level(roi: float) -> int | None:
    for lvl in LOSS_LEVELS:
        if roi <= lvl:
            return lvl
    return None


# ================================================================
# 🧠 NUEVO: build_operation_suggestion
# ================================================================
def build_operation_suggestion(analysis: dict, roi: float, loss_pct: float):
    """
    Traduce análisis técnico + pérdida → recomendación:
    🟢 Mantener
    🔴 Cerrar
    ⚠️ Revertir
    🟡 Evaluar
    """

    major = analysis.get("major_trend")
    bias = analysis.get("smart_bias")
    match_ratio = analysis.get("match_ratio", 0)
    reasons = []

    # --- Caso crítico: pérdida profunda (>70%) ---
    if roi <= -70:
        return "🔴 Cerrar", ["Pérdida mayor al 70%", "Riesgo extremo de liquidación"]

    # --- Si tendencia y sesgo van completamente en contra ---
    if (major == "bull" and analysis.get("direction") == "short") or \
       (major == "bear" and analysis.get("direction") == "long"):
        if loss_pct <= -30:
            return "⚠️ Revertir posición", ["Tendencia opuesta fuerte", "Pérdida elevada"]
        return "🔴 Cerrar", ["Tendencia completamente opuesta"]

    # --- Continuación a favor ---
    if bias == "continuation" and match_ratio >= 50:
        return "🟢 Mantener", ["Sesgo de continuación a favor", f"Match {match_ratio}%"]

    # --- Sesgo indeciso o divergente ---
    if bias == "indecision" or match_ratio < 40:
        return "🟡 Evaluar", ["Condiciones técnicas débiles o mixtas"]

    # Por defecto:
    return "🟡 Evaluar", ["Escenario técnico neutral"]


# ================================================================
# 🚨 Monitor de operaciones abiertas
# ================================================================
async def monitor_open_positions():
    logger.info("📡 Iniciando evaluación de operaciones abiertas…")

    positions = get_open_positions()

    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for pos in positions:
        try:
            symbol = (pos.get("symbol") or "").upper()
            side = (pos.get("side") or "").lower()
            direction = "long" if side == "buy" else "short"

            entry = float(pos.get("entryPrice") or 0)
            mark = float(pos.get("markPrice") or entry)
            pnl = float(pos.get("unrealisedPnl") or 0)
            lev = int(float(pos.get("leverage") or 20))

            if entry <= 0:
                logger.warning(f"⚠️ Entrada inválida: {pos}")
                continue

            roi = calculate_roi(entry, mark, direction, lev)
            loss_pct = calculate_loss_pct_from_roi(roi, lev)

            logger.info(
                f"🔎 {symbol} | {direction.upper()} x{lev} | ROI={roi:.2f}% | Entry={entry} Mark={mark}"
            )

            loss_level = compute_loss_level(roi)
            if loss_level is None:
                continue

            # ================================
            # 🔍 Análisis técnico profundo
            # ================================
            analysis = analyze_trend_core(
                symbol=symbol,
                direction=direction,
                context="operation",
                roi=roi,
                loss_pct=loss_pct,
            )

            # Nueva traducción → recomendación
            suggestion, reasons = build_operation_suggestion(
                analysis, roi, loss_pct
            )

            # ================================
            # 📤 Enviar alerta final al usuario
            # ================================
            notify_operation_recommendation({
                "symbol": symbol,
                "direction": direction,
                "roi": roi,
                "pnl": pnl,
                "loss_level": loss_level,
                "match_ratio": analysis.get("match_ratio", 0),
                "major_trend": analysis.get("major_trend"),
                "smart_bias": analysis.get("smart_bias"),
                "suggestion": suggestion,
                "reasons": reasons,
            })

        except Exception as e:
            logger.error(f"❌ Error evaluando operación {pos}: {e}")


async def start_operation_tracker():
    logger.info("🔄 Iniciando start_operation_tracker()...")

    while True:
        try:
            await monitor_open_positions()
        except Exception as e:
            logger.error(f"❌ Error en start_operation_tracker: {e}")
        await asyncio.sleep(20)
