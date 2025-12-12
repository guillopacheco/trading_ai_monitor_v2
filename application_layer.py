import logging

from config import TELEGRAM_BOT_TOKEN

# Notificaciones
from services.telegram_service.notifier import Notifier

# Application Services
from services.application.signal_service import SignalService
from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService

from services.telegram_service.command_bot import CommandBot
from services.coordinators.analysis_coordinator import AnalysisCoordinator

# Coordinadores
from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

from services.open_position_engine.open_position_engine import OpenPositionEngine
from services.open_position_engine.position_monitor import PositionMonitor
from services.positions_service.operation_tracker import OperationTracker

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    def __init__(self, notifier):
        self.notifier = notifier

        self.analysis_service = AnalysisService()
        self.analysis = AnalysisCoordinator(self.analysis_service, self.notifier)

        # ======================================================
        # 5) Configurar token del bot
        # ======================================================
        self.bot_token = TELEGRAM_BOT_TOKEN

        self.operation_tracker = OperationTracker()
        self.open_position_engine = OpenPositionEngine(
            notifier=self.notifier, tracker=self.operation_tracker
        )

        self.position_monitor = PositionMonitor(
            engine=self.open_position_engine, notifier=self.notifier
        )

        self.monitor_task = None

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ======================================================
    # MÉTODOS USADOS POR command_bot Y telegram_reader
    # ======================================================

    async def analyze(self, symbol: str, direction: str):
        """Análisis manual solicitado desde /analizar."""
        return await self.analysis.run(symbol, direction)

    async def manual_reactivate(self, symbol: str):
        """Forzar reactivación manual via /reactivar."""
        return await self.signal.manual_reactivate(symbol)

    async def manual_close(self, symbol: str):
        """Cerrar una posición manualmente."""
        return await self.position.force_close(symbol)

    async def manual_reverse(self, symbol: str, side: str):
        """Revertir una posición manualmente."""
        return await self.position.force_reverse(symbol, side)

    async def monitor_positions(self):
        """Activar monitoreo general de posiciones."""
        return await self.position.monitor()

    async def start_position_monitor(self):
        if self.monitor_task and not self.monitor_task.done():
            return False  # ya estaba corriendo

        self.monitor_task = asyncio.create_task(self.position_monitor.start())
        return True

    def stop_position_monitor(self):
        if self.position_monitor:
            self.position_monitor.stop()
            return True
        return False

    def is_monitor_running(self):
        if self.monitor_task and not self.monitor_task.done():
            return True
        return False
