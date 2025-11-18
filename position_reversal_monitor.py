"""
position_reversal_monitor.py — Optimizado (2025/11)
------------------------------------------------------------
Monitor de reversiones técnicas basado en:
✔ Análisis multi–TF real (5m, 15m, 1h, 4h)
✔ Divergencias inteligentes (RSI, MACD, Smart Divergence)
✔ Tendencia mayor (trend_system_final)
✔ ATR y clasificación de volatilidad
✔ Confirmación basada en match técnico global
✔ Alertas profesionales con recomendación inteligente

Se integra con:
- main.py  → bucle periódico
- command_bot.py → /reversion (modo run_once)
------------------------------------------------------------
"""

import asyncio
import logging
from typing import Dict, Any

from bybit_client import get_open_positions
from indicators import get_technical_data
from trend_system_final import analyze_and_format
from notifier import send_message

logger = logging.getLogger("position_reversal_monitor")


# ============================================================
# 🔢 Cambio porcentual sin apalancamiento
# ============================================================

def _compute_price_change(entry: float, mark: float, direction: str) -> float:
    """Retorna variación % sin apalancamiento."""
    if entry <= 0:
        return 0.0

    change = ((mark - entry) / entry) * 100
    if direction == "short":
        change *= -1

    return change


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
# 🧠 Detección avanzada de reversión (motor moderno)
# ============================================================

def detect_advanced_reversal(symbol: str, direction: str) -> Dict[str, Any]:
    """
    Usa el motor completo trend_system_final para:
    ✔ divergencias fuertes
    ✔ tendencia mayor (1h–4h)
    ✔ smart bias
    ✔ match técnico global
    """

    result, formatted = analyze_and_format(symbol, direction_hint=direction)

    divs = result.get("divergences", {})
    smart = (result.get("smart_bias") or "").lower()
    match_ratio = result.get("match_ratio", 0)
    major = (result.get("major_trend") or "").lower()

    # divergencias peligrosas
    bear_signal = any("bear" in (v or "").lower() for v in divs.values())
    bull_signal = any("bull" in (v or "").lower() for v in divs.values())

    if "bearish" in smart:
        bear_signal = True
    if "bullish" in smart:
        bull_signal = True

    # reversión fuerte por tendencia mayor
    major_flip = False
    if direction == "long" and "bajista" in major:
        major_flip = True
    if direction == "short" and "alcista" in major:
        major_flip = True

    # condición de reversión real
    advanced_reversal = (
        bear_signal if direction == "long" else bull_signal
    ) or major_flip

    return {
        "reversal": advanced_reversal,
        "divergences": divs,
        "smart": smart,
        "major_trend": major,
        "match_ratio": match_ratio,
        "formatted": formatted,
    }


# ============================================================
# 🚨 Monitor principal de reversiones
# ============================================================

async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    logger.info("🚨 Iniciando monitor avanzado de reversiones...")

    while True:
        try:
            positions = get_open_positions()

            if not positions:
                logger.info("📭 No hay posiciones abiertas.")
                if run_once:
                    break
                await asyncio.sleep(interval_seconds)
                continue

            checked, alerts = 0, 0

            for pos in positions:

                try:
                    symbol = pos.get("symbol")
                    side = (pos.get("side") or "").lower()
                    direction = "long" if side == "buy" else "short"

                    entry = float(pos.get("entryPrice") or 0)
                    mark = float(pos.get("markPrice") or entry)
                    lev = int(float(pos.get("leverage") or 20))

                    if not symbol or entry <= 0:
                        continue

                    checked += 1

                    price_change = _compute_price_change(entry, mark, direction)

                    # Solo revisar posiciones con pérdida > -3%
                    if price_change > -3:
                        continue

                    logger.info(
                        f"🔎 Revisando reversión en {symbol} — {direction.upper()} x{lev} "
                        f"(cambio {price_change:.2f}%)"
                    )

                    # ATR / volatilidad
                    tech = get_technical_data(symbol, intervals=["5m"])
                    atr_rel = tech.get("5m", {}).get("atr_rel", 0) or 0
                    volatility = classify_volatility(atr_rel)

                    # Análisis profundo (motor completo)
                    adv = detect_advanced_reversal(symbol, direction)

                    if not adv["reversal"]:
                        continue

                    alerts += 1

                    divs = adv["divergences"]
                    active_divs = ", ".join(
                        f"{k}: {v}"
                        for k, v in divs.items()
                        if v and v not in ["Ninguna", "None"]
                    ) or "Ninguna"

                    # Construcción del mensaje
                    msg = (
                        f"🚨 *Reversión técnica detectada en {symbol}*\n"
                        f"📉 Dirección original: *{direction.upper()}* (x{lev})\n"
                        f"💰 Pérdida sin apalancamiento: {price_change:.2f}%\n"
                        f"🌡️ Volatilidad: {volatility}\n"
                        f"🧪 Divergencias: {active_divs}\n"
                        f"📊 Tendencia mayor: {adv['major_trend'].upper() or 'N/A'}\n"
                        f"⚙️ Match técnico global: {adv['match_ratio']:.1f}%\n"
                        f"\n"
                        f"📌 *Recomendación:* Riesgo elevado. Revisar posición inmediatamente.\n"
                        f"\n"
                        f"{adv['formatted']}"
                    )

                    await asyncio.to_thread(send_message, msg)

                except Exception as e:
                    logger.error(f"❌ Error analizando posición: {e}")

            logger.info(
                f"✅ Reversion monitor: {checked} posiciones revisadas, {alerts} alertas emitidas."
            )

        except Exception as e:
            logger.error(f"❌ Error en monitor_reversals(): {e}")

        if run_once:
            break

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_reversals(interval_seconds=300, run_once=True))
