"""
operation_tracker.py
------------------------------------------------------------
Monitor inteligente de operaciones abiertas en Bybit.

Funciones:
✔ Lee posiciones abiertas desde bybit_client.get_open_positions()
✔ Calcula ROI y PnL real
✔ Detecta niveles de pérdida (−3, −5, −10, −20, −30, −50, −70)
✔ Obtiene ATR real y clasifica volatilidad (BAJA / MEDIA / ALTA)
✔ Integra trend_system_final para análisis profundo
✔ Genera recomendación inteligente basada en divergencias + tendencia
✔ Envía alerta mediante notifier.notify_operation_alert()

Este módulo NO toca la base de datos.
Es puramente operativo.
------------------------------------------------------------
"""

import logging
from typing import Dict, Any

from bybit_client import get_open_positions
from indicators import get_technical_data
from notifier import notify_operation_alert
from trend_system_final import analyze_and_format

logger = logging.getLogger("operation_tracker")


# ============================================================
# 🔣 Cálculo ROI y niveles de pérdida
# ============================================================

LOSS_LEVELS = [-3, -5, -10, -20, -30, -50, -70]


def compute_roi(entry: float, mark: float, leverage: int, direction: str) -> float:
    """Retorna ROI real considerando dirección y apalancamiento."""
    if entry <= 0:
        return 0.0

    roi = ((mark - entry) / entry) * 100
    if direction == "short":
        roi *= -1

    return roi * leverage


def compute_loss_level(roi: float) -> int | None:
    """Devuelve el nivel de pérdida alcanzado (-3, -5, etc)."""
    for level in LOSS_LEVELS:
        if roi <= level:
            return level
    return None


# ============================================================
# 🔥 Clasificación de volatilidad usando ATR relativo
# ============================================================

def classify_volatility(atr_rel: float) -> str:
    if atr_rel < 0.005:
        return "BAJA"
    if atr_rel < 0.015:
        return "MEDIA"
    return "ALTA"


# ============================================================
# 🧠 Nueva generación de recomendaciones (motor moderno)
# ============================================================

def build_suggestion(symbol: str, direction: str) -> str:
    """
    Genera recomendación basada en trend_system_final.
    Devuelve un texto breve y claro para las alertas automáticas.
    """

    try:
        result, _ = analyze_and_format(symbol, direction_hint=direction)

        match_ratio = result.get("match_ratio", 0)
        major = (result.get("major_trend") or "").lower()
        smart = (result.get("smart_bias") or "").lower()
        divs = result.get("divergences", {})

        # Divergencias fuertes
        has_bear = any("bear" in (x or "").lower() for x in divs.values()) or "bearish" in smart
        has_bull = any("bull" in (x or "").lower() for x in divs.values()) or "bullish" in smart

        # Tendencia mayor
        if direction == "long" and "bajista" in major:
            return "⚠️ Tendencia mayor en contra — considerar cierre"

        if direction == "short" and "alcista" in major:
            return "⚠️ Tendencia mayor en contra — considerar cierre"

        # Divergencias peligrosas
        if direction == "long" and has_bear:
            return "⚠️ Divergencia bajista — riesgo elevado"

        if direction == "short" and has_bull:
            return "⚠️ Divergencia alcista — riesgo elevado"

        # Match técnico
        if match_ratio >= 70:
            return "🟢 Señal técnica fuerte — mantener"

        if match_ratio >= 50:
            return "🟡 Señal ambigua — monitorear"

        return "🔴 Señal técnica débil — evaluar cierre"

    except Exception as e:
        return f"⚠️ Error técnico al generar recomendación ({e})"


# ============================================================
# 🚨 MONITOR PRINCIPAL
# ============================================================

def monitor_open_positions():
    """
    Monitor principal.
    Llamado por main.py como tarea en segundo plano (to_thread).

    Este módulo NO es async.
    """

    logger.info("📡 Revisando operaciones abiertas...")

    positions = get_open_positions()
    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for pos in positions:

        try:
            symbol = pos["symbol"].upper()
            side = pos.get("side", "").lower()

            direction = "long" if side == "buy" else "short"

            entry = float(pos.get("entryPrice") or 0)
            mark = float(pos.get("markPrice") or entry)
            leverage = int(float(pos.get("leverage") or 20))
            pnl = float(pos.get("unrealisedPnl") or 0)

            if entry <= 0:
                logger.warning(f"⚠️ Entrada inválida para posición: {pos}")
                continue

            # 1) ROI real
            roi = compute_roi(entry, mark, leverage, direction)
            loss_level = compute_loss_level(roi)

            logger.info(
                f"🔎 {symbol} | {direction.upper()} x{leverage} | "
                f"Entry={entry:.6f} Mark={mark:.6f} ROI={roi:.2f}%"
            )

            # No alertar operaciones sanas
            if loss_level is None:
                continue

            # 2) Técnicos rápidos para volatilidad
            tech = get_technical_data(symbol, intervals=["5m"])
            atr_rel = tech.get("5m", {}).get("atr_rel", 0) or 0
            volatility = classify_volatility(atr_rel)

            # 3) Recomendación avanzada (trend_system_final)
            suggestion = build_suggestion(symbol, direction)

            # 4) Enviar alerta al usuario
            notify_operation_alert(
                symbol=symbol,
                direction=direction,
                roi=roi,
                pnl=pnl,
                loss_level=loss_level,
                volatility=volatility,
                suggestion=suggestion
            )

        except Exception as e:
            logger.error(f"❌ Error evaluando operación {pos}: {e}")
