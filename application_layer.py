# application_layer.py
import logging

from services.telegram_service.notifier import Notifier
from services.coordinators.signal_coordinator import SignalCoordinator

# Estos existen en tu estructura. Si alguno cambia, lo adaptamos, pero no tocamos lógica.
from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService
from services.application.signal_service import SignalService

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Contrato estable:
    - SIEMPRE recibe bot
    - Construye notifier(bot)
    - Construye servicios/coordinators con dependencias mínimas
    """

    def __init__(self, bot):
        self.bot = bot

        # Notificador (requiere bot)
        self.notifier = Notifier(bot)

        # Servicios base
        self.signal_service = SignalService()
        self.analysis = AnalysisService()
        self.operation = OperationService(self.notifier)

        # Coordinators
        # Nota: SignalCoordinator en tu proyecto ya está operando en logs recientes.
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")
