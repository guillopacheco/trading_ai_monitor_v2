import logging
from typing import Any

from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService
from services.application.signal_service import SignalService

from services.coordinators.signal_coordinator import SignalCoordinator

# El coordinador de posiciones se deja para una fase posterior
# from services.coordinators.position_coordinator import PositionCoordinator

from services.open_position_engine.open_position_engine import OpenPositionEngine
from services.positions_service.operation_tracker import OperationTracker

from services.reactivation_engine.reactivation_engine import ReactivationEngine
from services.telegram_service.notifier import Notifier
from services.technical_engine import technical_engine as _technical_engine_module

logger = logging.getLogger("application_layer")


class TechnicalEngineAdapter:
    """
    Adaptador ASÍNCRONO sobre el motor técnico basado en funciones.

    Los coordinadores esperan algo como:

        await technical_engine.analyze(symbol, direction, context="entry")

    El módulo technical_engine.py expone una función síncrona analyze(...),
    así que este wrapper la llama dentro de una corrutina.
    """

    async def analyze(
        self,
        symbol: str,
        direction: str,
        context: str = "entry",
        **kwargs,
    ) -> dict:
        # analyze(symbol, direction_hint=..., context=...)
        return _technical_engine_module.analyze(
            symbol,
            direction_hint=direction,
            context=context,
            **kwargs,
        )


class ApplicationLayer:
    """
    Punto central de acceso de la aplicación.

    - Orquesta servicios, motores y coordinadores.
    - Es lo que usa main.py, CommandBot y los demonios de reactivación.
    """

    def __init__(self, bot: Any) -> None:
        """
        `bot` = instancia de telegram.Bot (bot_app.bot en main.py)
        Aquí creamos el Notifier a partir de ese bot.
        """
        # -----------------------------
        # Notificador único
        # -----------------------------
        self.notifier = Notifier(bot)

        # -----------------------------
        # Servicios base
        # -----------------------------
        self.analysis_service = AnalysisService()
        self.signal_service = SignalService()
        self.operation_service = OperationService(self.notifier)

        # -----------------------------
        # Motores
        # -----------------------------
        self.technical_engine = TechnicalEngineAdapter()
        self.reactivation_engine = ReactivationEngine()
        self.open_position_engine = OpenPositionEngine(
            notifier=self.notifier,
            tracker=OperationTracker(),
        )

        # -----------------------------
        # Coordinadores
        # -----------------------------
        # 🧠 Señales (entrada + reactivación avanzada)
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            technical_engine=self.technical_engine,
            reactivation_engine=self.reactivation_engine,
            notifier=self.notifier,
        )

        # Monitor de posiciones se deja para más adelante
        self.position = None  # placeholder para compatibilidad futura

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ======================================================
    # Métodos usados por CommandBot
    # ======================================================

    def get_status(self) -> str:
        """
        Usado por /estado.
        """
        return "✅ Core inicializado (analysis, signals, reactivación)"

    async def analyze_symbol(self, symbol: str, direction: str, chat_id: int) -> dict:
        """
        Ejecuta un análisis técnico completo y envía el resultado a Telegram.
        Usado por /analizar.
        """
        # 1) Ejecutar análisis (vía AnalysisService)
        result: dict = await self.analysis_service.analyze_symbol(
            symbol=symbol,
            direction=direction,
            context="entry",
        )

        # 2) Formatear mensaje
        text = self.analysis_service.format_for_telegram(
            symbol=symbol,
            direction=direction,
            result=result,
            context="entry",
        )

        # 3) Enviar a Telegram
        await self.notifier.safe_send(text, chat_id=chat_id)
        return result

    async def evaluate_reactivation(self, signal_id: int) -> Any:
        """
        Reactivación manual de una señal concreta (comando /reactivar).
        De momento dejamos placeholder sencillo.
        """
        logger.warning(
            "ℹ️ evaluate_reactivation(signal_id) aún no está implementado como "
            "comando manual. El monitor automático sigue usando auto_reactivate()."
        )
        await self.notifier.safe_send(
            "⚠️ Reactivación manual aún no está implementada.",
            chat_id=None,
        )
        return None

    # ------------------------------------------------------
    # Monitoreo de posiciones abiertas (placeholder)
    # ------------------------------------------------------

    async def start_position_monitor(self) -> None:
        """
        Arranca el monitor de posiciones abiertas.
        Por ahora sólo deja constancia en logs para no romper /revisar.
        """
        logger.warning("ℹ️ Monitor de posiciones aún no integrado en ApplicationLayer.")

    async def stop_position_monitor(self) -> None:
        """
        Detiene el monitor de posiciones abiertas.
        Placeholder compatible con /detener.
        """
        logger.warning(
            "ℹ️ stop_position_monitor() aún no integrado en ApplicationLayer."
        )
