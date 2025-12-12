import logging

from services.telegram_service.notifier import Notifier
from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService
from services.application.operation_service import OperationService

from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

from services.reactivation_engine.reactivation_engine import ReactivationEngine
from services.open_position_engine.open_position_engine import OpenPositionEngine

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa principal que conecta todos los servicios de alto nivel.
    """

    def __init__(self, bot):
        logger.info("⚙️ Inicializando ApplicationLayer...")

        # -----------------------------
        # NOTIFICADOR
        # -----------------------------
        self.notifier = Notifier(bot)
        logger.info("📬 Notifier configurado.")

        # -----------------------------
        # SERVICIOS BASE
        # -----------------------------
        self.signal_service = SignalService()
        # Operation Service
        self.operation_service = OperationService(self.notifier)

        self.analysis = AnalysisService()

        # -----------------------------
        # MOTORES
        # -----------------------------
        self.reactivation_engine = ReactivationEngine(
            technical_engine=self.analysis.engine, signal_service=self.signal_service
        )

        self.position_monitor = OpenPositionEngine(
            technical_engine=self.analysis.engine,
            position_service=self.operation_service,
            notifier=self.notifier,
        )

        # -----------------------------
        # COORDINADORES
        # -----------------------------
        self.signals = SignalCoordinator(
            signal_service=self.signal_service,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
            technical_engine=self.analysis.engine,
        )

        self.positions = PositionCoordinator(
            position_service=self.operation_service,
            position_monitor=self.position_monitor,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ------------------------------------------------------------------
    # ATAJOS PARA COMANDOS TELEGRAM
    # ------------------------------------------------------------------
    async def analyze_symbol(self, symbol, direction, chat_id):
        return await self.analysis.analyze_request(symbol, direction, chat_id)

    async def process_new_signal(self, signal):
        return await self.signals.process_new_signal(signal)

    async def evaluate_reactivation(self, signal):
        return await self.signals.evaluate_reactivation(signal)

    async def start_position_monitor(self):
        return await self.positions.start_monitor()

    async def stop_position_monitor(self):
        return await self.positions.stop_monitor()

    async def evaluate_positions_now(self):
        return await self.positions.evaluate_now()
