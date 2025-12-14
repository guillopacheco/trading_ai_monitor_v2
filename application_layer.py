# application_layer.py
import logging

from services.telegram_service.notifier import Notifier

from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService
from services.application.operation_service import OperationService

from services.reactivation_engine.reactivation_engine import ReactivationEngine

from services.coordinators.signal_coordinator import SignalCoordinator

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa de orquestación: centraliza wiring de servicios/coordinadores.
    IMPORTANTE:
    - bot es obligatorio (Notifier lo requiere)
    """

    def __init__(self, bot):
        if bot is None:
            raise TypeError(
                "ApplicationLayer.__init__() requiere bot (python-telegram-bot)."
            )

        # Infra
        self.notifier = Notifier(bot)

        # Services
        self.analysis = AnalysisService()
        self.signal_service = SignalService()
        self.operation_service = OperationService(self.notifier)

        # Engines
        self.reactivation_engine = ReactivationEngine()

        # Coordinators
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
