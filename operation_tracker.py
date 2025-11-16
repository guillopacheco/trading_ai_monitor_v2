"""
operation_tracker.py — Monitor inteligente de posiciones abiertas
-----------------------------------------------------------------
- Lee posiciones en tiempo real desde bybit_client
- Calcula ROI y PnL con apalancamiento
- Evalúa niveles de pérdida (-30, -50, -70, -90)
- Evalúa volatilidad por ATR relativo (1m)
- Analiza tendencia con trend_system_final.analyze_and_format()
- Recomienda mantener / cerrar / revertir
- Envía alertas automáticas vía notifier
"""

import logging
import asyncio

from bybit_client import get_open_positions, get_account_info
from indicators import get_technical_data
from trend_system_final import analyze_and_format
from notifier import notify_operation_alert

logger = logging.getLogger("operation_tracker")

LOSS_LEVELS = [-30, -50, -70, -90]  # niveles de pérdida progresivos


# ================================================================
# 🧠 Clasificación automática de acciones recomendadas
# ================================================================
def classify_operation_action(direction: str, match_ratio: float) -> str:
    """
    Decide la acción sugerida según coincidencia técnica:

    - ≥ 80%: mantener
    - 60–79%: evaluar (puede mejorar)
    - 40–59%: cerrar
    - < 40%: revertir (tendencia opuesta fuerte)
    """
    if match_ratio >= 80:
        return "MANTENER (tendencia todavía favorable)"
    elif 60 <= match_ratio < 80:
        return "EVALUAR — posible continuación si mejora"
    elif 40 <= match_ratio < 60:
        return "CERRAR — tendencia dudosa o mixta"
    else:
        if direction == "long":
            return "REVERTIR → la tendencia es claramente BAJISTA"
        else:
            return "REVERTIR → la tendencia es claramente ALCISTA"


# ================================================================
# 🔁 Bucle principal
# ================================================================
async def monitor_open_positions(poll_seconds: int = 60):
    """
    Supervisión continua de posiciones:
    - Obtiene posiciones cada poll_seconds
    - Evalúa ROI/PnL
    - Calcula volatilidad
    - Ejecuta análisis técnico multi-TF
    - Envía alertas automáticas
    """
    logger.info("🧭 Iniciando monitoreo de operaciones abiertas...")
    last_alert_level: dict[str, float] = {}

    while True:
        try:
            positions = get_open_positions()

            if not positions:
                logger.info("ℹ️ No hay posiciones activas. Reintentando...")
                await asyncio.sleep(poll_seconds)
                continue

            account = get_account_info()
            equity = float(account.get("totalEquity", 0) or 0)

            for pos in positions:
                symbol = pos.get("symbol")

                side = pos.get("side", "Buy")
                direction = "long" if side.lower() == "buy" else "short"

                entry = float(pos.get("entryPrice") or 0)
                mark = float(pos.get("markPrice") or entry)
                pnl = float(pos.get("unrealisedPnl", 0) or 0)
                size = float(pos.get("size") or 0)
                lev = int(float(pos.get("leverage", 20)))

                if size <= 0 or entry <= 0:
                    continue

                # =====================================================
                # 📈 ROI calculado correctamente con apalancamiento
                # =====================================================
                raw = (mark - entry) / entry
                if direction == "short":
                    raw = -raw
                roi = raw * lev * 100.0

                logger.info(
                    f"📊 {symbol}: {direction.upper()} | Entry={entry:.4f} | "
                    f"Mark={mark:.4f} | ROI={roi:.2f}% | PnL={pnl:.4f} USDT | Lev x{lev}"
                )

                # =====================================================
                # 🌡️ Volatilidad mediante ATR relativo (1m)
                # =====================================================
                try:
                    tech = get_technical_data(symbol, intervals=["1m"])
                    atr_rel = float(tech["1m"].get("atr_rel", 0))
                except Exception:
                    atr_rel = 0

                volatility = (
                    "LOW" if atr_rel < 0.01 else
                    "MEDIUM" if atr_rel < 0.02 else
                    "HIGH"
                )

                # =====================================================
                # 📉 Detección de nivel de pérdida alcanzado
                # =====================================================
                level_hit = None
                for lvl in LOSS_LEVELS:
                    if roi <= lvl:
                        level_hit = lvl

                if level_hit is None:
                    continue

                # Evitar spam: solo avisar si el ROI llegó a un nuevo nivel
                if symbol in last_alert_level and roi >= last_alert_level[symbol]:
                    continue

                # =====================================================
                # 📊 ANALISIS TÉCNICO COMPLETO / MULTI-TEMP
                # =====================================================
                try:
                    result, _ = analyze_and_format(symbol, direction_hint=direction)
                    match_ratio = result.get("match_ratio", 0.0)
                except Exception as e:
                    logger.error(f"⚠️ Error ejecutando análisis técnico para {symbol}: {e}")
                    match_ratio = 0

                # =====================================================
                # 🤖 Acción recomendada según match_ratio
                # =====================================================
                action = classify_operation_action(direction, match_ratio)

                # =====================================================
                # 🔔 ALERTA
                # =====================================================
                try:
                    notify_operation_alert(
                        symbol=symbol,
                        direction=direction,
                        roi=roi,
                        pnl=pnl,
                        loss_level=level_hit,
                        volatility=volatility,
                        suggestion=f"{action} — Match {match_ratio:.1f}%"
                    )
                    logger.info(f"🔔 Alerta enviada para {symbol}: {action}")
                except Exception as e:
                    logger.error(f"❌ No se pudo enviar alerta para {symbol}: {e}")

                last_alert_level[symbol] = roi

            await asyncio.sleep(poll_seconds)

        except asyncio.CancelledError:
            logger.warning("🛑 Monitor cancelado manualmente.")
            break

        except Exception as e:
            logger.error(f"❌ Error en monitor_open_positions(): {e}")
            await asyncio.sleep(poll_seconds)
