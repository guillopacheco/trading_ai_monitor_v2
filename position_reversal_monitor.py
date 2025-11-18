"""
position_reversal_monitor.py
------------------------------------------------------------
Monitor de reversiones técnicas en posiciones abiertas.

- Lee posiciones desde bybit_client.get_open_positions()
- Calcula cambio porcentual respecto al entry (sin apalancamiento)
- Solo analiza si hay pérdida relevante (por defecto < -3%)
- Obtiene datos técnicos multi–TF (5m, 15m) vía indicators.get_technical_data()
- Usa divergence_detector.detect_divergences() para RSI / MACD / Volumen
- Detecta cambio de tendencia contrario a la operación
- Envía una alerta a Telegram si:

    • Hay divergencias técnicas activas
    • Hay cambio de tendencia contra la dirección original

Este módulo NO toca la base de datos.
Se integra con:
- main.py  → tarea periódica (interval_seconds)
- command_bot.py → /reversion (run_once=True)
------------------------------------------------------------
"""

import asyncio
import logging
from typing import Dict, Any

from bybit_client import get_open_positions
from indicators import get_technical_data
from divergence_detector import detect_divergences
from notifier import send_message

logger = logging.getLogger("position_reversal_monitor")


# ============================================================
# 🔍 Núcleo de análisis de una posición
# ============================================================

def _compute_price_change(entry: float, mark: float, direction: str) -> float:
    """
    Devuelve el cambio porcentual del precio SIN apalancamiento.
    direction: 'long' o 'short'
    """
    if entry <= 0:
        return 0.0

    change = ((mark - entry) / entry) * 100.0
    if direction == "short":
        change *= -1

    return change


def _describe_divergences(divs: Dict[str, Any]) -> str:
    """
    Convierte el dict de divergencias en una frase legible.
    divs esperado:
        {"RSI": "...", "MACD": "...", "Volumen": "..."}
    """
    activos = [
        f"{k}: {v}"
        for k, v in divs.items()
        if v and v not in ["Ninguna", "None"]
    ]
    return ", ".join(activos) if activos else "Ninguna"


def _detect_trend_flip(direction: str, tech_multi: Dict[str, Dict[str, Any]]) -> str | None:
    """
    Revisa la tendencia en 5m y 15m (campo 'trend' que indicators ya setea)
    y devuelve 'alcista' / 'bajista' si detecta un giro significativo
    contra la operación original.
    """
    short_trend = (tech_multi.get("5m", {}).get("trend") or "").lower()
    mid_trend = (tech_multi.get("15m", {}).get("trend") or "").lower()

    # Para LONG, una reversión bajista es peligrosa
    if direction == "long" and ("bajista" in short_trend or "bear" in short_trend
                                or "bajista" in mid_trend or "bear" in mid_trend):
        return "bajista"

    # Para SHORT, una reversión alcista es peligrosa
    if direction == "short" and ("alcista" in short_trend or "bull" in short_trend
                                 or "alcista" in mid_trend or "bull" in mid_trend):
        return "alcista"

    return None


# ============================================================
# 🚨 Monitor principal de reversiones
# ============================================================

async def monitor_reversals(interval_seconds: int = 600, run_once: bool = False):
    """
    Monitorea posiciones abiertas y detecta reversiones técnicas:

    - Solo analiza posiciones con pérdida > ~ -3% (sin apalancamiento)
    - Si detecta divergencias o cambio fuerte de tendencia en 5m/15m
      envía alerta a Telegram con detalles.

    Parámetros:
    - interval_seconds: segundos entre revisiones (modo bucle)
    - run_once: si True, ejecuta solo una pasada y termina
    """
    logger.info("🚨 Iniciando monitor de reversiones de posiciones...")

    while True:
        try:
            positions = get_open_positions()
            if not positions:
                logger.info("📭 No hay posiciones abiertas para analizar.")
                if run_once:
                    break
                await asyncio.sleep(interval_seconds)
                continue

            checked = 0
            alerts = 0

            for pos in positions:
                try:
                    symbol = pos.get("symbol")
                    side = (pos.get("side") or "").lower()
                    direction = "long" if side == "buy" else "short"

                    entry = float(pos.get("entryPrice") or 0)
                    mark_price = float(pos.get("markPrice") or entry)
                    lev = int(float(pos.get("leverage") or 20))

                    if not symbol or entry <= 0:
                        logger.warning(f"⚠️ Datos inválidos para posición: {pos}")
                        continue

                    checked += 1

                    # Cambio porcentual sin apalancamiento
                    price_change = _compute_price_change(entry, mark_price, direction)

                    # Solo analizar si hay pérdida relevante (> -3%)
                    if price_change > -3:
                        continue

                    logger.info(
                        f"🔎 Revisando {symbol} ({direction.upper()} x{lev}) "
                        f"entry={entry:.6f}, mark={mark_price:.6f}, change={price_change:.2f}%"
                    )

                    # Datos técnicos multi-TF
                    tech_multi = get_technical_data(symbol, intervals=["5m", "15m"])
                    if not tech_multi:
                        logger.warning(f"⚠️ Sin datos técnicos para {symbol}")
                        continue

                    # Divergencias técnicas (usa divergence_detector.detect_divergences)
                    divs = detect_divergences(symbol, tech_multi)
                    has_divergence = any(
                        v and v not in ["Ninguna", "None"] for v in divs.values()
                    )

                    # Cambio de tendencia
                    new_trend = _detect_trend_flip(direction, tech_multi)

                    # Solo avisar si hay algo serio
                    if not has_divergence and not new_trend:
                        continue

                    alerts += 1
                    active_divs = _describe_divergences(divs)

                    lines = [
                        f"🚨 *Reversión potencial en {symbol}*",
                        f"🔹 Dirección original: *{direction.upper()}* (x{lev})",
                        f"💰 Cambio aprox. sin apalancamiento: {price_change:.2f}%",
                        f"🧪 Divergencias activas: {active_divs}",
                    ]

                    if new_trend:
                        lines.append(
                            f"📈 Cambio de tendencia en marcos cortos hacia: *{new_trend.upper()}*"
                        )

                    lines.append(
                        "📌 Recomendación: Revisar la posición; considerar cierre parcial/total "
                        "o incluso apertura en sentido contrario si el análisis global lo confirma."
                    )

                    # MUY IMPORTANTE: send_message es síncrona → usar to_thread
                    await asyncio.to_thread(send_message, "\n".join(lines))

                except Exception as e:
                    logger.error(f"❌ Error analizando posición individual: {e}")

            logger.info(
                f"✅ Monitor de reversiones: {checked} posiciones revisadas, {alerts} alertas emitidas."
            )

        except Exception as e:
            logger.error(f"❌ Error en monitor_reversals(): {e}")

        if run_once:
            break

        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(monitor_reversals(interval_seconds=300, run_once=True))
