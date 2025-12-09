# services/coordinators/position_coordinator.py

import logging
from services.application.operation_service import OperationService
from services.application.analysis_service import AnalysisService
from services.telegram_service.notifier import Notifier

logger = logging.getLogger("position_coordinator")


class PositionCoordinator:
    """
    Coordina:
    • Monitoreo de posiciones abiertas
    • Análisis técnico aplicado a posiciones activas
    • Cierre, reversión y protección avanzada
    """

    def __init__(self, operation_service: OperationService, analysis_service: AnalysisService, notifier: Notifier):
        self.op_service = operation_service
        self.analysis_service = analysis_service
        self.notifier = notifier

    # ============================================================
    # 1. Monitorear posiciones activas
    # ============================================================
    async def monitor(self):
        """
        Procesa todas las posiciones activas directamente desde Bybit.
        """
        positions = await self.op_service.get_positions()
        if not positions:
            logger.info("🔍 No hay posiciones abiertas actualmente.")
            return "🔍 No hay posiciones abiertas."

        for pos in positions:
            await self._process_single_position(pos)

        return "📊 Monitoreo completado."

    # ============================================================
    # 2. Procesar posición individual
    # ============================================================
    async def _process_single_position(self, pos):
        symbol = pos.get("symbol")
        pnl_pct = float(pos.get("pnlPct", 0))
        side = pos.get("side").lower()

        logger.info(f"📌 Procesando {symbol}: PNL {pnl_pct}%")

        # Obtener análisis técnico
        analysis = await self.analysis_service.analyze(symbol, side)

        # Reglas automáticas
        if pnl_pct <= -50:
            await self._handle_critical_loss(symbol, pos, analysis)
            return

        if pnl_pct <= -30:
            await self._handle_warning_loss(symbol, pos, analysis)
            return

        logger.info(f"ℹ️ {symbol}: situación estable ({pnl_pct}%).")

    # ============================================================
    # 3. Pérdida crítica (≥50%)
    # ============================================================
    async def _handle_critical_loss(self, symbol, pos, analysis):
        decision = analysis.get("decision", "wait")

        msg = (
            f"⚠️ **Pérdida crítica en {symbol} (-50%)**\n"
            f"• Recomendación del motor: **{decision}**"
        )
        await self.notifier.notify_position_event(msg)

        if decision == "close":
            await self.op_service.close(symbol, "critical_loss")

        elif decision == "reverse":
            await self.op_service.reverse(symbol, "critical_loss")

    # ============================================================
    # 4. Pérdida moderada (30–50%)
    # ============================================================
    async def _handle_warning_loss(self, symbol, pos, analysis):
        decision = analysis.get("decision", "wait")

        msg = (
            f"⚠️ **Pérdida moderada en {symbol} (-30%)**\n"
            f"• Recomendación del motor: **{decision}**"
        )

        await self.notifier.notify_position_event(msg)

    # ============================================================
    # 5. Cierre manual
    # ============================================================
    async def force_close(self, symbol):
        await self.op_service.close(symbol, "manual_close")
        await self.notifier.notify_position_event(f"🟪 Cierre manual ejecutado en {symbol}")
        return f"Cierre enviado para {symbol}"

    # ============================================================
    # 6. Reversión manual
    # ============================================================
    async def force_reverse(self, symbol):
        await self.op_service.reverse(symbol, "manual_reverse")
        await self.notifier.notify_position_event(f"🔄 Reversión ejecutada en {symbol}")
        return f"Reversión enviada para {symbol}"
