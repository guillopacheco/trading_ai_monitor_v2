# application_layer.py

from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService
from services.application.operation_service import OperationService
from services.coordinators.signal_coordinator import SignalCoordinator
from services.telegram_service.notifier import Notifier

import logging

logger = logging.getLogger(__name__)


class ApplicationLayer:
    def __init__(self):
        # Servicios base
        self.analysis = AnalysisService()
        self.signal_service = SignalService()
        self.operation = OperationService()
        self.notifier = Notifier()

        # Coordinadores (usan servicios)
        self.signal = SignalCoordinator(
            analysis=self.analysis,
            signal_service=self.signal_service,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
