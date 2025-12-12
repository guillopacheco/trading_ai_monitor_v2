import asyncio
import logging

from config import TELEGRAM_USER_ID

# Servicios de aplicación
from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService

# Notificador Telegram
from services.telegram_service.notifier import Notifier

# Motor técnico ya está integrado dentro de AnalysisService / technical_engine

# Motor de reactivación (usa el motor técnico internamente)
from services.reactivation_engine.reactivation_engine import ReactivationEngine

# Motor de operaciones abiertas
from services.open_position_engine.open_position_engine import OpenPositionEngine
from services.open_position_engine.position_monitor import PositionMonitor

# Tracker de operaciones (historial)
from services.positions_service.operation_tracker import OperationTracker

# Coordinadores (capa intermedia para el bot)
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

# Monitor de reactivación de señales (loop async)
from services.signals_service.signal_reactivation_sync import start_reactivation_monitor


logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa central de orquestación del Trading AI Monitor.

    Aquí se concentran:
      - Servicios de negocio (analysis_service, signal_service, etc.)
      - Motores avanzados (ReactvationEngine, OpenPositionEngine)
      - Monitores async (PositionMonitor, reactivation monitor)
      - Coordinadores usados por CommandBot
      - Notificador Telegram
    """

    def __init__(self):
        logger.info("⚙️ Inicializando ApplicationLayer...")

        # ----------------------------------------------------
        # 1) Notificador (sin bot aún)
        # ----------------------------------------------------
        # El bot real se inyecta luego con set_bot()
        self.notifier = Notifier()
        self.bot = None
        self.telegram_chat_id = TELEGRAM_USER_ID

        # ----------------------------------------------------
        # 2) Servicios base
        # ----------------------------------------------------
        self.signal_service = SignalService()
        self.analysis_service = AnalysisService()
        self.operation_tracker = OperationTracker()

        # ----------------------------------------------------
        # 3) Motores avanzados
        # ----------------------------------------------------
        # ReactivationEngine usa el motor técnico internamente
        self.reactivation_engine = ReactivationEngine()

        # Motor de operaciones abiertas
        self.open_position_engine = OpenPositionEngine(
            notifier=self.notifier,
            tracker=self.operation_tracker,
        )

        # Monitor async de posiciones abiertas
        self.position_monitor = PositionMonitor(
            engine=self.open_position_engine,
            notifier=self.notifier,
        )

        # Estado interno de monitores
        self._reactivation_task: asyncio.Task | None = None
        self._reactivation_running: bool = False

        self._position_monitor_task: asyncio.Task | None = None

        # ----------------------------------------------------
        # 4) Coordinadores (usados por CommandBot)
        # ----------------------------------------------------
        self.analysis = AnalysisCoordinator(
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        self.signals = SignalCoordinator(
            signal_service=self.signal_service,
            notifier=self.notifier,
            reactivation_engine=self.reactivation_engine,
        )

        self.positions = PositionCoordinator(
            position_monitor=self.position_monitor,
            notifier=self.notifier,
        )

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ========================================================
    # Inyección del bot (lo hace main.py después de crearlo)
    # ========================================================
    def set_bot(self, bot):
        """
        Configura el bot real en el Notifier.
        Esto se llama desde main.py después de crear Application.
        """
        self.bot = bot
        try:
            self.notifier.configure(bot=bot, chat_id=self.telegram_chat_id)
            logger.info("📨 Notifier configurado con bot y chat_id.")
        except Exception as e:
            logger.error(f"❌ Error configurando Notifier: {e}", exc_info=True)

    # ========================================================
    # API para CommandBot y otros módulos
    # ========================================================

    async def analyze_symbol(self, symbol: str, direction: str, chat_id: int):
        """
        Análisis bajo demanda desde /analizar.

        Delegamos en AnalysisCoordinator, que:
        - Llama al motor técnico
        - Formatea el mensaje
        - Envía el resultado vía Notifier
        """
        try:
            await self.analysis.analyze_request(symbol, direction, chat_id)
        except Exception as e:
            logger.error(
                f"❌ Error en analyze_symbol({symbol}, {direction}): {e}", exc_info=True
            )
            # fallback mínimo
            if self.notifier:
                await self.notifier.safe_send(
                    f"❌ Error analizando {symbol} {direction}"
                )

    async def evaluate_reactivation(self, signal_id: int):
        """
        Reactivación manual de una señal desde /reactivar.

        Por ahora, dejamos un comportamiento seguro:
        - Loguea la petición
        - Notifica que aún no está implementado manualmente
        - La reactivación automática la maneja el monitor background
        """
        logger.info(f"🟦 Solicitud manual de reactivación para señal ID={signal_id}.")
        if self.notifier:
            await self.notifier.safe_send(
                f"ℹ️ Reactivación manual para ID={signal_id} aún no está implementada.\n"
                f"La reactivación automática está activa mediante el monitor de señales."
            )

    # ========================================================
    # Monitores async
    # ========================================================

    async def start_reactivation_monitor(self):
        """
        Inicia (si no está iniciado) el monitor de reactivación de señales.
        Usa la función async de signal_reactivation_sync.
        """
        if self._reactivation_running:
            logger.info("🔁 Monitor de reactivación ya estaba en ejecución.")
            return

        try:
            logger.info("🔁 Iniciando monitor de reactivación de señales...")
            # Lanzamos el loop como tarea en segundo plano
            self._reactivation_task = asyncio.create_task(
                start_reactivation_monitor(self)
            )
            self._reactivation_running = True
        except Exception as e:
            logger.error(
                f"❌ Error iniciando monitor de reactivación: {e}", exc_info=True
            )

    async def start_position_monitor(self):
        """
        Inicia el monitor de posiciones abiertas.
        Se usa desde /reanudar.
        """
        if self._position_monitor_task and not self._position_monitor_task.done():
            logger.info("📡 PositionMonitor ya está activo.")
            return

        logger.info("📡 Iniciando PositionMonitor (operaciones abiertas)...")
        try:
            self._position_monitor_task = asyncio.create_task(
                self.position_monitor.start()
            )
        except Exception as e:
            logger.error(f"❌ Error iniciando PositionMonitor: {e}", exc_info=True)

    async def stop_position_monitor(self):
        """
        Detiene el monitor de posiciones abiertas (si estaba activo).
        Se usa desde /detener.
        """
        try:
            if self.position_monitor:
                self.position_monitor.stop()
                logger.info("⏹ PositionMonitor detenido.")
        except Exception as e:
            logger.error(f"❌ Error deteniendo PositionMonitor: {e}", exc_info=True)

    # ========================================================
    # Estado global — usado por /estado
    # ========================================================

    def get_status(self) -> dict:
        """
        Devuelve un diccionario con el estado del sistema,
        para que CommandBot lo use en /estado.
        """
        position_monitor_running = bool(
            self._position_monitor_task and not self._position_monitor_task.done()
        )

        return {
            "reactivation_running": self._reactivation_running,
            "position_monitor_running": position_monitor_running,
            "telegram_user": self.telegram_chat_id,
        }
