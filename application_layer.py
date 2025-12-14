# application_layer.py
import logging

from services.telegram_service.notifier import Notifier
from services.coordinators.signal_coordinator import SignalCoordinator
from services.reactivation_engine.reactivation_engine import ReactivationEngine

from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService
from services.application.signal_service import SignalService

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    def __init__(self, bot):
        self.bot = bot

        # 1️⃣ Notifier (depende de bot)
        self.notifier = Notifier(bot)

        # 2️⃣ Servicios base
        self.signal_service = SignalService()
        self.analysis = AnalysisService()
        self.operation = OperationService(self.notifier)

        # 3️⃣ ReactivationEngine (EXISTE y ya lo usas)
        self.reactivation_engine = ReactivationEngine(notifier=self.notifier)

        # 4️⃣ SignalCoordinator (CONSTRUCTOR COMPLETO)
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
