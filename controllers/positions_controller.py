"""
positions_controller.py
------------------------
Controlador oficial para monitorear posiciones abiertas en Bybit,
aplicar análisis técnico avanzado y enviar recomendaciones al usuario.

Este módulo reemplaza:
    - operation_tracker.py
    - position_reversal_monitor.py

Flujo:
    scheduler → positions_controller → bybit_service → signal_engine → telegram_service
"""

import asyncio
import logging
from datetime import datetime

from services.bybit_service import get_open_positions, get_symbol_price
from services.telegram_service import send_message
from services import db_service
from core.signal_engine import analyze_reversal, analyze_signal

logger = logging.getLogger("positions_controller")


# ============================================================
# 🔵 PARÁMETROS DEL MONITOR
# ============================================================
DEFAULT_INTERVAL_MIN = 10   # 10 minutos
FAST_INTERVAL_MIN = 5       # alta volatilidad detectada

LOSS_LEVELS = {
    30: "🟡 Advertencia moderada",
    50: "🟠 Riesgo alto, evaluar cierre o reversión",
    70: "🔴 Riesgo extremo, tendencia totalmente en contra",
    90: "⚫ Pérdida crítica, acción inmediata requerida",
}


# ============================================================
# 🔵 LOOP PRINCIPAL DEL MONITOR
# ============================================================
class PositionsMonitor:
    """
    Controlador de ciclo continuo de monitoreo de posiciones.
    """

    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        if self.running:
            logger.warning("⚠️ PositionsMonitor ya está activo.")
            return

        self.running = True
        self.task = asyncio.create_task(self._loop())
        await send_message("📡 Monitor de posiciones activado.")
        logger.info("PositionsMonitor iniciado.")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        await send_message("🛑 Monitor de posiciones detenido.")
        logger.info("PositionsMonitor detenido.")

    async def _loop(self):
        """
        Ciclo continuo: obtiene posiciones → las evalúa → espera → repite.
        """

        while self.running:
            try:
                await self.evaluate_positions()
            except Exception as e:
                logger.error(f"❌ Error en evaluate_positions(): {e}")

            # TODO: cambiar a intervalos dinámicos según ATR
            await asyncio.sleep(DEFAULT_INTERVAL_MIN * 60)


# ============================================================
# 🔵 EVALUACIÓN DE POSICIONES
# ============================================================
    async def evaluate_positions(self):
        positions = await get_open_positions()

        if not positions:
            logger.info("📭 No hay posiciones abiertas.")
            return

        logger.info(f"📊 Evaluando {len(positions)} posiciones abiertas…")

        for pos in positions:
            try:
                await self.evaluate_single_position(pos)
            except Exception as e:
                logger.error(f"❌ Error evaluando posición {pos}: {e}")


# ============================================================
# 🔵 LÓGICA POR POSICIÓN
# ============================================================
    async def evaluate_single_position(self, pos):
        """
        Estructura estándar de position (según bybit_service):

        {
            "symbol": "BTCUSDT",
            "side": "Buy" / "Sell",
            "entry_price": 42000.0,
            "size": 0.1,
            "unrealized_pnl": -12.5,
            "pnl_pct": -33.5
        }
        """

        symbol = pos["symbol"]
        direction = "long" if pos["side"] == "Buy" else "short"
        pnl_pct = pos["pnl_pct"]

        logger.info(f"🔍 Posición {symbol} ({direction}) PnL: {pnl_pct}%")

        # Guardar en DB
        db_service.add_position_log(
            symbol=symbol,
            direction=direction,
            pnl_pct=pnl_pct,
            timestamp=datetime.utcnow().isoformat()
        )

        # 1️⃣ Pérdida baja → solo monitoreo
        if pnl_pct > -30:
            logger.info("🟢 Posición estable, sin acciones adicionales.")
            return

        # 2️⃣ Pérdida moderada → primera advertencia
        if -50 < pnl_pct <= -30:
            await send_message(f"🟡 {symbol} pierde {pnl_pct}%. Revisando tendencia…")
            await self._run_reversal_check(symbol, direction)
            return

        # 3️⃣ Pérdida alta → posible reversión
        if -70 < pnl_pct <= -50:
            await send_message(f"🟠 {symbol} está en -{abs(pnl_pct)}%. Evaluando si cerrar o revertir…")
            await self._run_reversal_check(symbol, direction, high_risk=True)
            return

        # 4️⃣ Pérdida extrema → acción urgente
        if pnl_pct <= -70:
            await send_message(f"🔴 {symbol} llegó a -{abs(pnl_pct)}%. Tendencia crítica.")
            await self._run_reversal_check(symbol, direction, emergency=True)
            return


# ============================================================
# 🔵 ANÁLISIS DE REVERSIÓN
# ============================================================
    async def _run_reversal_check(self, symbol, direction, high_risk=False, emergency=False):
        """
        Llama al motor técnico unificado para detectar si la tendencia
        se ha invertido totalmente o si la operación puede recuperarse.
        """

        try:
            analysis = await analyze_reversal(symbol, direction)
        except Exception as e:
            logger.error(f"❌ Error en analyze_reversal(): {e}")
            return

        decision = analysis.get("decision")
        match_ratio = analysis.get("match_ratio")
        grade = analysis.get("grade")

        # Construcción del mensaje
        msg = (
            f"📉 **Revisión de reversión — {symbol}**\n"
            f"Match Ratio: {match_ratio}%\n"
            f"Grado: {grade}\n"
            f"Decisión: {decision}\n\n"
        )

        # 🔥 Decision path
        if decision == "keep":
            msg += "🟢 La posición aún puede recuperarse.\n"
            await send_message(msg)
            return

        if decision == "close":
            msg += "🔴 Tendencia fuerte en contra. Se recomienda cerrar la posición."
            await send_message(msg)
            return

        if decision == "reverse":
            msg += "⚡ Tendencia completamente contraria. **Se recomienda revertir posición.**"
            await send_message(msg)
            return

        # fallback
        msg += "⚠ No se pudo determinar una recomendación clara."
        await send_message(msg)
