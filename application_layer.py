# application_layer.py
import logging

from services.telegram_service.notifier import Notifier
from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService
from services.application.operation_service import OperationService

from services.reactivation_engine.reactivation_engine import ReactivationEngine
from services.coordinators.signal_coordinator import SignalCoordinator

from services.open_position_engine.open_position_engine import OpenPositionEngine
from services.positions_service.operation_tracker import OperationTracker

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    ✅ Contrato estable:
    - SIEMPRE recibe bot (pero tolera None para tests).
    - Construye todo aquí.
    """

    def __init__(self, bot=None):
        self.bot = bot

        # Notifier tolerante
        self.notifier = Notifier(bot=self.bot)

        # Services
        self.analysis_service = AnalysisService()
        self.signal_service = SignalService()
        self.operation_service = OperationService(notifier=self.notifier)

        # Engines
        self.reactivation_engine = ReactivationEngine()

        # Coordinators
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        # Open positions
        self.operation_tracker = OperationTracker()
        self.open_position_engine = OpenPositionEngine(
            notifier=self.notifier, tracker=self.operation_tracker
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
