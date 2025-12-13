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

        # Notifier (tu Notifier actual puede ser self.configure(...) o directo; aquí lo dejamos simple)
        self.notifier = Notifier()
        try:
            # Si tu Notifier soporta configure(bot, chat_id) lo usamos.
            # Si no existe, no rompe.
            self.notifier.configure(
                bot=bot, chat_id=getattr(self.notifier, "chat_id", None)
            )
        except Exception:
            # Si tu Notifier en tu versión se inyecta distinto, NO rompemos init por esto.
            pass

        # Motor técnico: AnalysisService envuelve services/technical_engine/technical_engine.py
        self.analysis_service = AnalysisService()

        # Señales + reactivación
        self.signal_service = SignalService()
        self.reactivation_engine = ReactivationEngine(
            technical_engine=self.analysis_service
        )

        # Coordinator de señales (la firma real debe coincidir con TU archivo actual)
        # Ajuste: le pasamos lo que más consistentemente necesita: signal_service, analysis_service, reactivation_engine, notifier
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
