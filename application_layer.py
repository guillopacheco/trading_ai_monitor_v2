import logging

from services.telegram_service.notifier import Notifier

from services.application.signal_service import SignalService
from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService

from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

from services.reactivation_engine.reactivation_engine import ReactivationEngine

from services.open_position_engine.open_position_engine import OpenPositionEngine
from services.open_position_engine.position_monitor import PositionMonitor

from services.positions_service.operation_tracker import OperationTracker


logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Clúster central del sistema.
    Conecta servicios, coordinadores y motores tácticos.
    """

    def __init__(self, bot):

        logger.info("⚙️ Inicializando ApplicationLayer...")

        # ----------------------------------------------------
        # NOTIFICADOR
        # ----------------------------------------------------
        self.notifier = Notifier(bot)

        # ----------------------------------------------------
        # SERVICIOS BASE
        # ----------------------------------------------------
        self.signal_service = SignalService()
        self.analysis_service = AnalysisService()
        self.operation_service = OperationService(self.notifier)

        # ----------------------------------------------------
        # MOTORES DE APOYO
        # ----------------------------------------------------
        self.reactivation_engine = ReactivationEngine()  # <-- antes NO existía

        self.operation_tracker = OperationTracker()

        self.open_position_engine = OpenPositionEngine(
            notifier=self.notifier,
            tracker=self.operation_tracker,
        )

        self.position_monitor = PositionMonitor(
            engine=self.open_position_engine,
            notifier=self.notifier,
        )

        # ----------------------------------------------------
        # COORDINADORES (interfaz de alto nivel)
        # ----------------------------------------------------
        self.signal = SignalCoordinator(
            self.signal_service,
            self.reactivation_engine,
            self.notifier,
            self.analysis_service,  # technical_engine real
        )

        self.analysis = AnalysisCoordinator(
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        self.position = PositionCoordinator(
            monitor=self.position_monitor,
            tracker=self.operation_tracker,
            notifier=self.notifier,
        )

        # Monitor async
        self._monitor_task = None

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ============================================================
    # ATAJOS PARA USO POR BOTS/comandos
    # ============================================================

    async def analizar_manual(self, symbol: str, direction: str, chat_id: int):
        await self.analysis.analyze_request(symbol, direction, chat_id)

    async def procesar_senal_telegram(self, signal):
        await self.signal.process_new_signal(signal)

    # ============================================================
    # CONTROL DEL MONITOR DE POSICIONES ABIERTAS
    # ============================================================

    async def start_open_positions_monitor(self):
        import asyncio

        if self._monitor_task and not self._monitor_task.done():
            logger.info("ℹ️ PositionMonitor ya estaba activo.")
            return

        logger.info("▶️ Iniciando PositionMonitor...")

        self._monitor_task = asyncio.create_task(self.position_monitor.start())

    async def stop_open_positions_monitor(self):
        logger.info("⏹ Deteniendo PositionMonitor...")
        if self.position_monitor:
            self.position_monitor.stop()
        self._monitor_task = None

    def is_monitor_running(self) -> bool:
        return self.position_monitor.is_running()
