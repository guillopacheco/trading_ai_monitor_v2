# application_layer.py

import logging

from services.telegram_service.notifier import Notifier

from services.application.signal_service import SignalService
from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService

from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

from services.open_position_engine.open_position_engine import OpenPositionEngine
from services.open_position_engine.position_monitor import PositionMonitor
from services.positions_service.operation_tracker import OperationTracker

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa orquestadora de alto nivel.

    Aquí se conectan:
    - Servicios de aplicación (signals, analysis, operations)
    - Coordinadores (señales, análisis bajo demanda, posiciones)
    - Motores tácticos (open_position_engine + position_monitor)
    """

    def __init__(self, notifier: Notifier):
        logger.info("⚙️ Inicializando ApplicationLayer...")
        self.notifier = notifier

        # -----------------------------
        # Servicios base
        # -----------------------------
        self.signal_service = SignalService()
        self.analysis_service = AnalysisService()
        self.operation_service = OperationService(self.notifier)

        # -----------------------------
        # Motor táctico de posiciones abiertas
        # -----------------------------
        self.operation_tracker = OperationTracker()
        self.open_position_engine = OpenPositionEngine(
            notifier=self.notifier,
            tracker=self.operation_tracker,
        )
        self.position_monitor = PositionMonitor(
            engine=self.open_position_engine,
            notifier=self.notifier,
        )

        # -----------------------------
        # Coordinadores de alto nivel
        # -----------------------------
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        self.analysis = AnalysisCoordinator(
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        self.position = PositionCoordinator(
            operation_service=self.operation_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        self._monitor_task = None

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ============================================================
    # Atajos usados por command_bot / telegram_reader
    # ============================================================

    async def analizar_manual(self, symbol: str, direction: str, chat_id: int):
        """
        Wrapper para /analizar <symbol> <long|short>
        """
        await self.analysis.analyze_request(symbol, direction, chat_id)

    async def procesar_senal_telegram(self, signal):
        """
        Llamado desde telegram_reader cuando llega una señal del canal VIP.
        """
        await self.signal.process_new_signal(signal)

    # ============================================================
    # Control del monitor de posiciones abiertas (Punto C)
    # ============================================================

    async def start_open_positions_monitor(self):
        """
        Inicia el monitor de posiciones abiertas en background.
        Lo ideal es que command_bot lo llame desde un comando tipo /monitor_on.
        """
        if self._monitor_task and not self._monitor_task.done():
            logger.info("ℹ️ Monitor de posiciones ya estaba en ejecución.")
            return

        logger.info("▶️ Iniciando PositionMonitor...")
        # PositionMonitor.start() es un bucle async infinito controlado por su flag interno.
        # Lo envolvemos en un task para no bloquear.
        import asyncio

        self._monitor_task = asyncio.create_task(self.position_monitor.start())

    async def stop_open_positions_monitor(self):
        logger.info("⏹ Deteniendo PositionMonitor...")
        if self.position_monitor:
            self.position_monitor.stop()
        self._monitor_task = None

    def is_monitor_running(self) -> bool:
        return self.position_monitor.is_running()
