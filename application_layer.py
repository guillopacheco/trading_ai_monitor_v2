import logging
from config import TELEGRAM_BOT_TOKEN

from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa principal que coordina todos los servicios.
    Cada coordinador se encarga de un caso de uso específico.
    """

    def __init__(self):
        logger.info("⚙️ Inicializando ApplicationLayer...")

        # Token del bot de Telegram
        self.bot_token = TELEGRAM_BOT_TOKEN

        # Coordinadores
        self.signal = SignalCoordinator()
        self.analysis = AnalysisCoordinator()
        self.position = PositionCoordinator()

        logger.info("🧩 ApplicationLayer inicializado correctamente.")

    async def start(self):
        """Arranca servicios coordinados (si aplica)."""
        logger.info("🟢 ApplicationLayer → start() ejecutado (OK).")
