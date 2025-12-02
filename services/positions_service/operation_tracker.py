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
✔ Compatible con modo REAL y SIMULACIÓN.
--------------------------------------------------------------------
"""
import logging
import asyncio
from typing import Dict, Any

from services.technical_engine.trend_system_final import analyze_trend_core
from services.bybit_service.bybit_client import get_open_positions
from services.telegram_service.notifier import send_message

from core.helpers import (
    calculate_roi,
    calculate_loss_pct_from_roi,
    calculate_pnl,
)

logger = logging.getLogger("operation_tracker")

# Niveles de pérdida considerados críticos (ROI con apalancamiento)
LOSS_LEVELS = [-20, -30, -50, -70]


# ============================================================
# 🔢 Detección del nivel de pérdida
# ============================================================

def compute_loss_level(roi: float) -> int | None:
    for lvl in LOSS_LEVELS:
        if roi <= lvl:
            return lvl
    return None


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

            # ROI real (con apalancamiento)
            roi = calculate_roi(
                entry_price=entry,
                current_price=mark,
                direction=direction,
                leverage=lev,
            )

            # Pérdida sin apalancamiento aproximada
            loss_pct = calculate_loss_pct_from_roi(roi, lev)

            logger.info(
                f"🔎 {symbol} | {direction.upper()} x{lev} | ROI={roi:.2f}% | Entry={entry} Mark={mark}"
            )

            loss_level = compute_loss_level(roi)
            if loss_level is None:
                # Operación sin pérdidas críticas → no molestamos
                continue

            # =======================================================
            # 🔍 Análisis técnico profundo via trend_system_final
            # =======================================================
            analysis = analyze_trend_core(
                symbol=symbol,
                direction=direction,
                context="operation",
                roi=roi,          # ROI con apalancamiento
                loss_pct=loss_pct # pérdida aproximada sin apalancamiento
            )

            # =======================================================
            # 🎯 Recomendación final
            # =======================================================
            decision = analysis.get("decision", "")
            reasons = analysis.get("decision_reasons", [])

            if decision == "hold":
                suggestion = "🟢 Mantener"
            elif decision == "watch":
                suggestion = "🟡 Evaluar con precaución"
            elif decision == "close":
                suggestion = "🔴 Cerrar"
            elif decision == "revert":
                suggestion = "⚠️ Revertir posición"
            else:
                suggestion = "📊 Evaluar"

            if reasons:
                suggestion += "\n📝 Motivos:\n - " + "\n - ".join(reasons)

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


# ============================================================
# 🏁 Servicio programado — usado por main.py
# ============================================================

async def start_operation_tracker():
    """
    Bucle que ejecuta monitor_open_positions() cada 20 segundos.
    """
    logger.info("🔄 Iniciando start_operation_tracker()...")

    while True:
        try:
            await monitor_open_positions()
        except Exception as e:
            logger.error(f"❌ Error en start_operation_tracker: {e}")
        await asyncio.sleep(20)  # intervalo estándar
