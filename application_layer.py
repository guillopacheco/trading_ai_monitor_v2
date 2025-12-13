# application_layer.py

import logging

from services.telegram_service.notifier import Notifier
from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService

from services.reactivation_engine.reactivation_engine import ReactivationEngine
from services.coordinators.signal_coordinator import SignalCoordinator

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Contenedor de dependencias (DI simple).
    Construye servicios y coordinadores con firmas estables.
    """

    def __init__(self, bot):
        self.bot = bot

        # Notifier (PTB bot)
        self.notifier = Notifier(bot)

        # Services
        self.analysis_service = AnalysisService()
        self.signal_service = SignalService()

        # Engines
        self.reactivation_engine = ReactivationEngine()

        # Coordinators
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
