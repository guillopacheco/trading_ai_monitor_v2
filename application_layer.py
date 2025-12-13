# application_layer.py
import logging

from services.telegram_service.notifier import Notifier
from services.application.analysis_service import AnalysisService

from services.reactivation_engine.reactivation_engine import ReactivationEngine
from services.application.signal_service import SignalService

from services.coordinators.signal_coordinator import SignalCoordinator

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa central: arma dependencias y expone APIs coherentes para:
    - CommandBot (/analizar)
    - Telegram reader (señales entrantes)
    - Reactivation monitor
    - (más adelante) open_position_engine
    """

    def __init__(self, bot):
        logger.info("⚙️ Inicializando ApplicationLayer...")

        self.notifier = Notifier(bot)

        self.analysis_service = AnalysisService()
        self.signal_service = SignalService()

        self.reactivation_engine = ReactivationEngine(self.analysis_service)

        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    async def analyze_symbol(
        self, symbol: str, direction: str, context: str = "entry"
    ) -> dict:
        """
        API única para análisis manual o por señal.
        """
        return await self.analysis_service.analyze_symbol(
            symbol, direction, context=context
        )
