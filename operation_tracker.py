"""
operation_tracker.py — Monitor inteligente de posiciones abiertas
-----------------------------------------------------------------
Versión optimizada (2025-11)

Funciones principales:
✔ Lee posiciones abiertas desde bybit_client
✔ Calcula ROI real con apalancamiento ×20
✔ Evalúa niveles de pérdida (-30, -50, -70, -90)
✔ Evalúa volatilidad (ATR relativo 1m)
✔ Analiza tendencia mayor (multi-TF)
✔ Analiza divergencias peligrosas
✔ Recomienda mantener, cerrar, revertir o evaluar
✔ Envía alertas de riesgo al usuario
✔ Evita spam y duplicados
"""

import logging
import asyncio

from bybit_client import get_open_positions, get_account_info
from indicators import get_technical_data
from trend_system_final import analyze_and_format
from notifier import notify_operation_alert

logger = logging.getLogger("operation_tracker")

LOSS_LEVELS = [-30, -50, -70, -90]  # niveles progresivos


# ================================================================
# 🧠 Mejorado: Filtro de divergencias para evitar decisiones malas
# ================================================================
def _dangerous_divergence(result: dict, direction: str) -> bool:
    divs = result.get("divergences", {})
    smart_bias = (result.get("smart_bias") or "").lower()

    rsi = (divs.get("RSI") or "").lower()
    macd = (divs.get("MACD") or "").lower()

    if direction == "long":
        if "bear" in rsi or "bear" in macd:
            return True
        if "bearish" in smart_bias:
            return True

    if direction == "short":
        if "bull" in rsi or "bull" in macd:
            return True
        if "bullish" in smart_bias:
            return True

    return False


# ================================================================
# 🧭 Evaluación de tendencia mayor (1h y superiores)
# ================================================================
def _major_trend_invalid(result: dict, direction: str) -> bool:
    """
    Si la tendencia mayor contradice tu operación, se recomienda salida.
    """
    major = (result.get("major_trend") or "").lower()

    if direction == "long" and "bajista" in major:
        return True

    if direction == "short" and "alcista" in major:
        return True

    return False


# ================================================================
# 🧮 Acción recomendada basada en match_ratio + tendencia real
# ================================================================
def classify_operation_action(direction: str, result: dict, roi: float) -> str:
    match_ratio = result.get("match_ratio", 0.0)

    # 1. divergencias peligrosas (prioridad)
    if _dangerous_divergence(result, direction):
        return "CERRAR — Divergencia fuerte detectada"

    # 2. tendencia mayor contradictoria
    if _major_trend_invalid(result, direction):
        if roi > 0:
            return "CERRAR — Tendencia mayor en contra (tome ganancias)"
        return "REVERTIR — Tendencia mayor opuesta"

    # 3. Clasificación estándar
    if match_ratio >= 80:
        return "MANTENER — tendencia favorable"
    elif 60 <= match_ratio < 80:
        return "EVALUAR — posible continuación"
    elif 40 <= match_ratio < 60:
        return "CERRAR — tendencia dudosa"
    else:
        return "REVERTIR — tendencia opuesta fuerte"


# ================================================================
# 🔁 Monitor en tiempo real
# ================================================================
async def monitor_open_positions(poll_seconds: int = 60):
    logger.info("🧭 Iniciando monitor de posiciones abiertas...")
    last_alert_level: dict[str, float] = {}

    while True:
        try:
            positions = get_open_positions()

            if not positions:
                logger.info("ℹ️ No hay posiciones abiertas.")
                await asyncio.sleep(poll_seconds)
                continue

            account = get_account_info()
            equity = float(account.get("totalEquity", 0) or 0)

            for pos in positions:
                symbol = pos.get("symbol")
                side = pos.get("side", "Buy")
                direction = "long" if side.lower() == "buy" else "short"

                entry = float(pos.get("entryPrice"))
                mark = float(pos.get("markPrice"))
                lev = int(float(pos.get("leverage", 20)))
                pnl = float(pos.get("unrealisedPnl", 0))

                # ROI calculado correctamente
                raw = (mark - entry) / entry
                if direction == "short":
                    raw = -raw
                roi = raw * lev * 100.0

                logger.info(
                    f"📌 {symbol}: {direction.upper()} | ROI={roi:.2f}% | PnL={pnl:.4f}"
                )

                # ----------------------------------------------------
                # 🌡️ Volatilidad ATR
                # ----------------------------------------------------
                try:
                    tech = get_technical_data(symbol, intervals=["1m"])
                    atr_rel = tech["1m"].get("atr_rel", 0)
                except Exception:
                    atr_rel = 0

                volatility = (
                    "LOW" if atr_rel < 0.01 else
                    "MEDIUM" if atr_rel < 0.02 else
                    "HIGH"
                )

                # ----------------------------------------------------
                # 🔻 Detectar nivel de pérdida alcanzado
                # ----------------------------------------------------
                level_hit = None
                for lvl in LOSS_LEVELS:
                    if roi <= lvl:
                        level_hit = lvl

                if level_hit is None:
                    continue

                # Evitar spam
                if symbol in last_alert_level and roi >= last_alert_level[symbol]:
                    continue

                # ----------------------------------------------------
                # 📊 Analizar tendencia real
                # ----------------------------------------------------
                result, _message = analyze_and_format(symbol, direction_hint=direction)
                action = classify_operation_action(direction, result, roi)

                # ----------------------------------------------------
                # 🔔 Enviar alerta automática
                # ----------------------------------------------------
                try:
                    notify_operation_alert(
                        symbol=symbol,
                        direction=direction,
                        roi=roi,
                        loss_level=level_hit,
                        volatility=volatility,
                        suggestion=f"{action} — Match {result.get('match_ratio', 0):.1f}%"
                    )
                    logger.info(f"🔔 Alerta enviada para {symbol}: {action}")
                except Exception as e:
                    logger.error(f"❌ Error enviando alerta: {e}")

                last_alert_level[symbol] = roi

            await asyncio.sleep(poll_seconds)

        except asyncio.CancelledError:
            logger.warning("🛑 Monitor de posiciones cancelado.")
            break

        except Exception as e:
            logger.error(f"❌ Error en monitor_open_positions(): {e}")
            await asyncio.sleep(poll_seconds)
