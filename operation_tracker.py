"""
operation_tracker.py (versión final)
------------------------------------------------------------
Monitor moderno de operaciones activas usando technical_brain.py

Funciones:
✔ Lee posiciones desde bybit_client.get_open_positions()
✔ Calcula ROI y PnL reales
✔ Evalúa ATR, divergencias y tendencia
✔ Usa technical_brain.analyze_for_reversal()
✔ Genera recomendaciones profesionales
✔ Envía alerta mediante notifier.notify_operation_alert()

Este módulo NO toca la base de datos.
------------------------------------------------------------
"""

import logging
from typing import Dict, Any

from bybit_client import get_open_positions
from technical_brain import analyze_for_reversal
from notifier import send_message

logger = logging.getLogger("operation_tracker")


# ============================================================
# 🔢 ROI REAL
# ============================================================

def compute_roi(entry: float, mark: float, lev: int, direction: str) -> float:
    """ROI real con dirección y apalancamiento."""
    if entry <= 0:
        return 0.0
    roi = ((mark - entry) / entry) * 100.0
    if direction == "short":
        roi *= -1
    return roi * lev


# ============================================================
# 🔍 Núcleo del monitor
# ============================================================

def monitor_open_positions():
    """
    Llamado desde main.py mediante asyncio.to_thread():
    Revisa operaciones activas y envía alertas automáticas.
    """

    logger.info("📡 Evaluando operaciones activas...")

    positions = get_open_positions()
    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    for pos in positions:

        try:
            # ================================
            # Extraer datos de la operación
            # ================================
            symbol = pos["symbol"].upper()
            side = pos.get("side", "").lower()
            direction = "long" if side == "buy" else "short"

            entry = float(pos.get("entryPrice") or 0)
            mark = float(pos.get("markPrice") or entry)
            lev = int(float(pos.get("leverage") or 20))
            pnl = float(pos.get("unrealisedPnl") or 0)

            if entry <= 0:
                logger.warning(f"⚠️ Entrada inválida en posición: {pos}")
                continue

            # ================================
            # ROI real
            # ================================
            roi = compute_roi(entry, mark, lev, direction)

            logger.info(
                f"🧾 Posición {symbol} | {direction.upper()} x{lev}\n"
                f"  Entry={entry:.6f} | Mark={mark:.6f} | ROI={roi:.2f}%"
            )

            # ================================
            # Ejecutar análisis completo
            # ================================
            analysis = analyze_for_reversal(
                symbol=symbol,
                direction=direction,
                entry_price=entry,
                mark_price=mark,
                leverage=lev,
                roi=roi
            )

            allowed = analysis["allowed"]
            suggestion = analysis["suggestion"]
            atr = analysis["atr"]
            divs = analysis["divergences"]
            trends = analysis["trend_multi"]
            short_bias = analysis["short_bias"]

            # ================================
            # Si la operación es relativamente sana → no alertar
            # ================================
            if allowed:
                continue

            # ================================
            # Preparar reporte detallado
            # ================================
            msg = [
                f"⚠️ *Alerta crítica en {symbol}*",
                f"📌 Dirección original: *{direction.upper()}* x{lev}",
                f"💰 ROI actual: {roi:.2f}%",
                f"📉 PnL: {pnl:.4f} USDT",
                "",
                f"📊 *Tendencias:*",
                f"• 5m: {trends['5m']}",
                f"• 15m: {trends['15m']}",
                f"• 1h: {trends['1h']}",
                "",
                f"🧪 *Divergencias:*",
                f"RSI: {divs['RSI']}",
                f"MACD: {divs['MACD']}",
                "",
                f"🌡️ ATR (volatilidad): {atr}",
                f"🔎 Sesgo corto (short-bias): {short_bias}",
                "",
                f"🧠 *Recomendación:* {suggestion}",
                "",
                "👉 *Considera cerrar parcial, total o revertir dependiendo del contexto.*"
            ]

            send_message("\n".join(msg))

        except Exception as e:
            logger.error(f"❌ Error evaluando operación {pos}: {e}")
