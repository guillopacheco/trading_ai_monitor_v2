import logging

from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService
from services.application.signal_service import SignalService

from services.telegram_service.notifier import Notifier

from services.technical_engine.technical_engine import TechnicalEngine
from services.reactivation_engine.reactivation_engine import ReactivationEngine

from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

from services.open_position_engine.open_position_engine import OpenPositionEngine

logger = logging.getLogger("application_layer")


class ApplicationLayer:

    def __init__(self, bot):
        logger.info("⚙️ Inicializando ApplicationLayer...")

        # 1) Notificador
        self.notifier = Notifier(bot)

        # 2) Servicios base
        self.signal_service = SignalService()
        self.operation_service = OperationService(self.notifier)

        # 3) Motor técnico (base)
        self.technical_engine = TechnicalEngine()

        # 4) Motor de reactivación avanzada
        self.reactivation_engine = ReactivationEngine(
            technical_engine=self.technical_engine,
            signal_service=self.signal_service,
            notifier=self.notifier,
        )

        # 5) Servicio de análisis (requiere technical_engine)
        self.analysis = AnalysisService(self.technical_engine)

        # 6) Coordinador de señales (requiere analysis, notifier y reactivation_engine)
        self.signal = SignalCoordinator(
            self.signal_service,
            self.analysis,
            self.notifier,
            self.technical_engine,
            self.reactivation_engine,
        )

        # 7) Motor de operaciones abiertas
        self.open_position_engine = OpenPositionEngine(
            technical_engine=self.technical_engine,
            operation_service=self.operation_service,
            notifier=self.notifier,
        )

        # 8) Coordinador de posiciones
        self.position = PositionCoordinator(
            self.operation_service, self.open_position_engine, self.notifier
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
