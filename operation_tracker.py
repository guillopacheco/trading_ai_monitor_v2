"""
operation_tracker.py — versión final integrada con trend_system_final
--------------------------------------------------------------------
Monitor inteligente de operaciones abiertas en Bybit.

Funciones principales:
✔ Obtiene operaciones abiertas desde bybit_client.get_open_positions()
✔ Calcula ROI real con helpers.calculate_roi()
✔ Evalúa pérdida, tendencia y sesgo smart
✔ Produce recomendaciones claras: mantener / cerrar / revertir
✔ Envía alertas automáticas vía notifier.send_message()

Compatible con modo REAL y SIMULACIÓN.
--------------------------------------------------------------------
"""

import logging
import asyncio
from typing import Dict, Any

from bybit_client import get_open_positions
from notifier import send_message
from helpers import calculate_roi
from trend_system_final import analyze_trend_core, _get_thresholds

logger = logging.getLogger("operation_tracker")

# Niveles de pérdida considerados críticos
LOSS_LEVELS = [-3, -5, -10, -20, -30, -50, -70]


# ============================================================
# 🔢 Detección del nivel de pérdida
# ============================================================

def compute_loss_level(roi: float) -> int | None:
    for lvl in LOSS_LEVELS:
        if roi <= lvl:
            return lvl
    return None


# ============================================================
# 🧠 Recomendación basada en trend_system_final
# ============================================================

def build_recommendation(direction: str, analysis: Dict[str, Any], roi: float) -> str:
    """
    Usa el análisis unificado (trend_system_final) para producir
    una recomendación clara y coherente.
    """

    match_ratio = analysis.get("match_ratio", 0.0)
    major_trend = analysis.get("major_trend", "").lower()
    smart_bias = analysis.get("smart_bias", "").lower()
    recommendation = analysis.get("recommendation", "")
    thresholds = _get_thresholds()
    internal_threshold = thresholds.get("internal", 55.0)

    dir_lower = direction.lower()

    # 1. Pérdidas grandes → acciones duras
    if roi <= -20:
        # Tendencia mayor en contra = cierre o reversión inmediata
        if (dir_lower == "long" and "bear" in major_trend) or \
           (dir_lower == "short" and "bull" in major_trend):
            return "❌ Tendencia mayor en contra + pérdida elevada: cerrar o revertir."

        # Smart bias en contra
        if (dir_lower == "long" and "bear" in smart_bias) or \
           (dir_lower == "short" and "bull" in smart_bias):
            return "⚠️ Smart bias adverso: alta probabilidad de continuación en contra."

    # 2. Si la señal está técnicamente revalidada (match alto)
    if match_ratio >= internal_threshold:
        if roi > 0:
            return "🟢 Operación saludable, mantener."
        return "🟡 Señal técnica coherente, pero pérdida moderada: vigilar."

    # 3. Sesgo en contra
    if (dir_lower == "long" and "bear" in smart_bias) or \
       (dir_lower == "short" and "bull" in smart_bias):
        return "⚠️ Smart bias desfavorable: evaluar cierre."

    # 4. Recomendación técnica del motor
    if recommendation:
        return recommendation

    # 5. Caso estable
    if -5 < roi < 5:
        return "⏳ Movimiento neutro, continuar monitoreando."

    return "📊 Evaluación estándar basada en condiciones actuales."


# ============================================================
# 🚨 Monitor principal de operaciones
# ============================================================

async def monitor_open_positions():
    """
    Revisa todas las posiciones abiertas en Bybit y genera alertas
    cuando la tendencia o la pérdida justifican una acción.
    """

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

            # ROI real (with leverage)
            roi = calculate_roi(
                entry_price=entry,
                current_price=mark,
                direction=direction,
                leverage=lev,
            )

            logger.info(
                f"🔎 {symbol} | {direction.upper()} x{lev} | ROI={roi:.2f}% | Entry={entry} Mark={mark}"
            )

            loss_level = compute_loss_level(roi)
            if loss_level is None:
                # Operación sin pérdidas críticas
                continue

            # =======================================================
            # 🔍 Análisis técnico profundo via trend_system_final
            # =======================================================
            analysis = analyze_trend_core(symbol, direction_hint=direction)

            # =======================================================
            # 🎯 Recomendación final
            # =======================================================
            suggestion = build_recommendation(direction, analysis, roi)

            # =======================================================
            # 📩 Notificación al usuario
            # =======================================================
            alert_msg = (
                f"🚨 *Alerta de operación: {symbol}*\n"
                f"📌 Dirección: *{direction.upper()}* x{lev}\n"
                f"💵 ROI: `{roi:.2f}%`\n"
                f"💰 PnL: `{pnl}`\n"
                f"📉 Nivel de pérdida: {loss_level}%\n"
                f"📊 Match técnico: {analysis.get('match_ratio', 0):.1f}%\n"
                f"🧭 Tendencia mayor: {analysis.get('major_trend')}\n"
                f"🔮 Sesgo smart: {analysis.get('smart_bias')}\n"
                f"🧠 *Recomendación:* {suggestion}"
            )

            await asyncio.to_thread(send_message, alert_msg)

        except Exception as e:
            logger.error(f"❌ Error evaluando operación {pos}: {e}")
