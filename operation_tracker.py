"""
operation_tracker.py — Monitor inteligente de posiciones abiertas
---------------------------------------------------------------
- Lee posiciones desde bybit_client (real o simulado)
- Calcula ROI y evalúa niveles de pérdida (-30, -50, -70, -90)
- Evalúa volatilidad con ATR relativo (via indicators)
- Llama analyze_trend() para sugerencias automáticas
- Envía alertas progresivas via notifier
"""

import logging
import asyncio
from bybit_client import get_open_positions, get_ohlcv_data
from indicators import get_technical_data
from trend_analysis import analyze_trend
from notifier import notify_operation_alert, send_message

logger = logging.getLogger("operation_tracker")

LOSS_LEVELS = [-30, -50, -70, -90]  # niveles de pérdida progresivos


async def monitor_open_positions(poll_seconds: int = 60):
    """
    Bucle asíncrono para supervisar posiciones abiertas activamente.
    Evalúa ROI, volatilidad y tendencia; envía alertas automáticas.
    """
    logger.info("🧭 Iniciando monitoreo de operaciones abiertas...")
    last_alert_level: dict[str, int] = {}  # symbol -> último nivel avisado

    while True:
        try:
            positions = get_open_positions()
            if not positions:
                logger.info("ℹ️ No hay posiciones activas. Reintentando más tarde...")
                await asyncio.sleep(poll_seconds)
                continue

            for pos in positions:
                symbol = pos["symbol"]
                direction = pos["direction"].lower()
                entry = float(pos["entry"] or 0)
                lev = int(pos.get("leverage", 20) or 20)

                # === Precio actual ===
                df = get_ohlcv_data(symbol, "1", limit=100)
                if df is None or df.empty:
                    logger.warning(f"⚠️ Sin OHLCV reciente para {symbol}")
                    continue

                current = float(df["close"].iloc[-1])
                roi = 0.0
                if entry > 0:
                    raw = (current - entry) / entry
                    if direction == "short":
                        raw = -raw
                    roi = raw * lev * 100.0

                # === Volatilidad simple (ATR relativo) ===
                tech = get_technical_data(symbol, intervals=["1m"])
                atr_rel = 0.0
                if tech and "1m" in tech:
                    atr_rel = float(tech["1m"].get("atr_rel", 0) or 0)
                volatility = (
                    "LOW" if atr_rel < 0.01 else
                    "MEDIUM" if atr_rel < 0.02 else
                    "HIGH"
                )

                # === Detección de pérdida significativa ===
                loss_level_hit = None
                for lvl in LOSS_LEVELS:
                    if roi <= lvl:
                        loss_level_hit = lvl
                if loss_level_hit is not None:
                    prev = last_alert_level.get(symbol)
                    if prev is None or loss_level_hit < prev:
                        suggestion = "Evaluar tendencia y considerar cerrar o revertir."

                        # === Enriquecimiento con análisis multi-TF ===
                        try:
                            tech_multi = get_technical_data(symbol, intervals=["1m", "5m", "15m"])
                            if tech_multi:
                                tr = analyze_trend(symbol, direction, entry, tech_multi, lev)
                                rec = tr.get("recommendation", "EVALUAR")
                                match = tr.get("match_ratio", 0)
                                suggestion = f"{rec} (match {match:.2f})"
                        except Exception as err:
                            logger.warning(f"⚠️ analyze_trend falló para {symbol}: {err}")

                        # === Notificar alerta ===
                        notify_operation_alert(
                            symbol=symbol,
                            direction=direction,
                            roi=roi,
                            loss_level=loss_level_hit,
                            volatility=volatility,
                            suggestion=suggestion,
                        )

                        last_alert_level[symbol] = loss_level_hit

            await asyncio.sleep(poll_seconds)

        except asyncio.CancelledError:
            logger.warning("🛑 Monitor de posiciones cancelado.")
            break
        except Exception as e:
            logger.error(f"❌ Error en monitor_open_positions(): {e}")
            await asyncio.sleep(poll_seconds)
