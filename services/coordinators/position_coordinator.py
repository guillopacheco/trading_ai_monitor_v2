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

    def __init__(self, notifier: Notifier):
        self.notifier = notifier
        self.op_service = OperationService()
        self.analysis_service = AnalysisService()

    # ============================================================
    # 1. Monitorear posiciones activas
    # ============================================================
    async def monitor_positions(self):
        """
        Procesa todas las posiciones activas directamente desde Bybit.
        """
        positions = await self.op_service.get_open_positions()
        if not positions:
            logger.info("🔍 No hay posiciones abiertas actualmente.")
            return

        for pos in positions:
            await self._process_single_position(pos)

    # ============================================================
    # 2. Procesar posición individual
    # ============================================================
    async def _process_single_position(self, pos):
        symbol = pos.get("symbol")
        pnl_pct = float(pos.get("pnlPct", 0))
        side = pos.get("side")

        logger.info(f"📌 Procesando {symbol}: PNL {pnl_pct}%")

        # Obtener análisis técnico para esta posición
        analysis = await self.analysis_service.analyze_symbol(symbol, side)

        # Reglas críticas
        if pnl_pct <= -50:
            await self._handle_critical_loss(symbol, pos, analysis)
            return

        if pnl_pct <= -30:
            await self._handle_warning_loss(symbol, pos, analysis)
            return

        # Sin registrar eventos en DB (no existe la función)
        logger.info(f"💾 Evento registrado (virtual): {symbol} analizado")

    # ============================================================
    # 3. Pérdida crítica (≥50%)
    # ============================================================
    async def _handle_critical_loss(self, symbol, pos, analysis):
        decision = analysis.get("decision")

        msg = (
            f"⚠️ **Pérdida crítica en {symbol} (-50%)**\n"
            f"• Acción recomendada: {decision}"
        )
        await self.notifier.notify_position_event(msg)

        if decision == "close":
            await self.op_service.close_position(symbol)

        elif decision == "reverse":
            await self.op_service.reverse_position(symbol)

    # ============================================================
    # 4. Pérdida moderada (30–50%)
    # ============================================================
    async def _handle_warning_loss(self, symbol, pos, analysis):
        decision = analysis.get("decision")

        msg = (
            f"⚠️ **Pérdida moderada en {symbol} (-30%)**\n"
            f"• Acción recomendada: {decision}"
        )
        await self.notifier.notify_position_event(msg)

    # ============================================================
    # 5. Cierre manual
    # ============================================================
    async def manual_close(self, symbol):
        await self.op_service.close_position(symbol)
        await self.notifier.notify_position_event(f"🟪 Cierre manual ejecutado en {symbol}")

    # ============================================================
    # 6. Reversión manual
    # ============================================================
    async def manual_reverse(self, symbol, side):
        await self.op_service.reverse_position(symbol, side)
        await self.notifier.notify_position_event(f"🔄 Reversión ejecutada en {symbol} → {side}")
