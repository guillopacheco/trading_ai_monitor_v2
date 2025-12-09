import logging

from config import TELEGRAM_BOT_TOKEN

# Notificaciones
from services.telegram_service.notifier import Notifier

# Application Services
from services.application.signal_service import SignalService
from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService

# Coordinadores
from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.position_coordinator import PositionCoordinator


logger = logging.getLogger("application_layer")


class ApplicationLayer:

    def __init__(self):
        logger.info("⚙️ Inicializando ApplicationLayer...")

        # ======================================================
        # 2) Crear notificador global
        # ======================================================
        self.notifier = Notifier()

        # ======================================================
        # 3) Instanciar servicios de aplicación
        # ======================================================
        self.signal_service = SignalService()
        self.analysis_service = AnalysisService()
        self.operation_service = OperationService(self.notifier)

        # ======================================================
        # 4) Instanciar coordinadores (capa de dominio)
        # ======================================================
        self.signal = SignalCoordinator(
            self.signal_service,
            self.analysis_service,
            self.notifier
        )
        self.signal_coordinator = self.signal  # alias para reactivación

        self.analysis = AnalysisCoordinator(
            self.analysis_service,
            self.notifier
        )

        self.position = PositionCoordinator(
            self.operation_service,
            self.analysis_service,
            self.notifier
        )

        # ======================================================
        # 5) Configurar token del bot
        # ======================================================
        self.bot_token = TELEGRAM_BOT_TOKEN

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
