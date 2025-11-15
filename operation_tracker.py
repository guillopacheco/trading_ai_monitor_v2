"""
operation_tracker.py — Monitor inteligente de posiciones abiertas
-----------------------------------------------------------------
- Lee posiciones desde bybit_client (real o simulado)
- Calcula ROI y PnL en tiempo real
- Evalúa niveles de pérdida (-30, -50, -70, -90)
- Evalúa volatilidad (ATR relativo)
- Analiza tendencia con analyze_trend()
- Envía alertas automáticas vía notifier
"""

import logging
import asyncio
from bybit_client import get_open_positions, get_ohlcv_data, get_account_info
from indicators import get_technical_data
from trend_analysis import analyze_trend
from notifier import notify_operation_alert

logger = logging.getLogger("operation_tracker")

LOSS_LEVELS = [-30, -50, -70, -90]  # niveles de pérdida progresivos


async def monitor_open_positions(poll_seconds: int = 60):
    """
    Bucle asíncrono que supervisa posiciones abiertas activamente.
    Evalúa ROI, PnL y volatilidad en tiempo real; genera alertas automáticas.
    """
    logger.info("🧭 Iniciando monitoreo de operaciones abiertas...")
    last_alert_level: dict[str, float] = {}  # símbolo -> último ROI avisado

    while True:
        try:
            positions = get_open_positions()
            if not positions:
                logger.info("ℹ️ No hay posiciones activas. Reintentando más tarde...")
                await asyncio.sleep(poll_seconds)
                continue

            account = get_account_info()
            equity = float(account.get("totalEquity", 0) or 0)

            for pos in positions:
                symbol = pos.get("symbol")
                side = pos.get("side", "Buy")
                direction = "long" if side.lower() == "buy" else "short"
                entry = float(pos.get("entryPrice") or 0)
                size = float(pos.get("size") or 0)
                lev = int(float(pos.get("leverage", 20)))
                mark_price = float(pos.get("markPrice") or entry)
                pnl = float(pos.get("unrealisedPnl", 0) or 0)

                if size <= 0:
                    continue
                if entry <= 0:
                    logger.warning(f"⚠️ Precio de entrada inválido para {symbol}: {entry}")
                    continue

                # === ROI y PnL ===
                try:
                    raw = (mark_price - entry) / entry
                    if direction == "short":
                        raw = -raw
                    roi = raw * lev * 100.0
                except ZeroDivisionError:
                    logger.error(f"❌ Error: división por cero en {symbol} (entry={entry})")
                    continue

                # 💰 Mostrar PnL y ROI en tiempo real
                logger.info(
                    f"📊 {symbol}: {direction.upper()} | Entry={entry:.4f} | Mark={mark_price:.4f} | "
                    f"ROI={roi:.2f}% | PnL={pnl:.2f} USDT | Size={size}"
                )

                # === Volatilidad relativa (ATR) ===
                try:
                    tech = get_technical_data(symbol, intervals=["1m"])
                    atr_rel = float(tech["1m"].get("atr_rel", 0)) if tech and "1m" in tech else 0.0
                except Exception as e:
                    atr_rel = 0.0
                    logger.warning(f"⚠️ No se pudo calcular volatilidad para {symbol}: {e}")

                volatility = (
                    "LOW" if atr_rel < 0.01 else
                    "MEDIUM" if atr_rel < 0.02 else
                    "HIGH"
                )

                # === Detectar niveles de pérdida ===
                loss_level_hit = None
                for lvl in LOSS_LEVELS:
                    if roi <= lvl:
                        loss_level_hit = lvl

                # Alerta temprana de pérdida o cambio de tendencia
                if roi <= -30 and (symbol not in last_alert_level or roi < last_alert_level[symbol]):
                    suggestion = "⚠️ Pérdida significativa detectada. Evaluar reversión."

                    # === Análisis técnico multi-TF ===
                    try:
                        tech_multi = get_technical_data(symbol, intervals=["1m", "5m", "15m"])
                        if tech_multi:
                            trend_result = analyze_trend(symbol, direction, entry, tech_multi, lev)
                            rec = trend_result.get("recommendation", "EVALUAR")
                            match = trend_result.get("match_ratio", 0)
                            suggestion = f"{rec} (Match {match:.2f})"
                    except Exception as err:
                        logger.warning(f"⚠️ analyze_trend falló para {symbol}: {err}")

                    # === Enviar alerta de operación ===
                    try:
                        notify_operation_alert(
                            symbol=symbol,
                            direction=direction,
                            roi=roi,
                            pnl=pnl,
                            loss_level=loss_level_hit or -30,
                            volatility=volatility,
                            suggestion=suggestion,
                        )
                        logger.info(f"🔔 Alerta enviada para {symbol} (ROI={roi:.2f}%)")
                    except Exception as e:
                        logger.error(f"❌ No se pudo enviar alerta para {symbol}: {e}")

                    last_alert_level[symbol] = roi

            await asyncio.sleep(poll_seconds)

        except asyncio.CancelledError:
            logger.warning("🛑 Monitor de posiciones cancelado manualmente.")
            break
        except Exception as e:
            logger.error(f"❌ Error en monitor_open_positions(): {e}")
            await asyncio.sleep(poll_seconds)
