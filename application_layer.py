import logging
from typing import Any, Dict

from services.telegram_service.notifier import Notifier
from services.application.analysis_service import AnalysisService
from services.application.signal_service import SignalService
from services.application.operation_service import OperationService
from services.coordinators.analysis_coordinator import AnalysisCoordinator
from services.coordinators.signal_coordinator import SignalCoordinator
from services.coordinators.position_coordinator import PositionCoordinator

logger = logging.getLogger("application_layer")


class ApplicationLayer:
    """
    Capa orquestadora de la aplicación.

    Centraliza:
    - Servicios de dominio (signals, analysis, operations)
    - Coordinadores (análisis bajo demanda, señales, posiciones)
    - Utilidades para el bot de comandos (CommandBot)
    """

    def __init__(self, notifier: Notifier):
        """
        Se instancia desde main.py, que ya construyó el bot de Telegram y el Notifier.
        """
        self.notifier = notifier

        # ------------------------------------------------------------------
        # Servicios base
        # ------------------------------------------------------------------
        self.signal_service = SignalService()
        self.analysis_service = AnalysisService()
        self.operation_service = OperationService(self.notifier)

        # ------------------------------------------------------------------
        # Coordinadores
        # ------------------------------------------------------------------
        # 🔍 Análisis bajo demanda (/analizar)
        self.analysis = AnalysisCoordinator(
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        # 📡 Señales (entrada + reactivación básica)
        self.signal = SignalCoordinator(
            signal_service=self.signal_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        # 📉 Posiciones abiertas (drawdown, etc.)
        self.position = PositionCoordinator(
            operation_service=self.operation_service,
            analysis_service=self.analysis_service,
            notifier=self.notifier,
        )

        # ------------------------------------------------------------------
        # Estado interno simple, usado por /estado
        # ------------------------------------------------------------------
        self.reactivation_running: bool = False
        self.position_monitor_running: bool = False

        logger.info("✅ ApplicationLayer inicializado correctamente.")

    # ======================================================================
    # 🔎 Consultas de estado para /estado
    # ======================================================================
    def get_status(self) -> Dict[str, Any]:
        """
        Devuelve un dict con el estado básico del sistema para /estado.
        """
        return {
            "reactivation_running": self.reactivation_running,
            "position_monitor_running": self.position_monitor_running,
            # Si quieres, luego puedes rellenar esto con TELEGRAM_USER_ID u otro dato.
            "telegram_user": "N/A",
        }

    # ======================================================================
    # 📌 /analizar SYMBOL long|short
    # ======================================================================
    async def analyze_symbol(self, symbol: str, direction: str, chat_id: int) -> None:
        """
        Ejecuta un análisis técnico bajo demanda y envía el resultado al chat.

        Lo delegamos al AnalysisCoordinator, que:
        - llama a AnalysisService
        - formatea el mensaje
        - y usa el Notifier para enviarlo.
        """
        try:
            await self.analysis.analyze_request(symbol, direction, chat_id)
        except Exception as e:
            logger.exception(f"❌ Error en analyze_symbol({symbol}, {direction}): {e}")
            # Enviamos un fallback directo usando el bot del notifier.
            if getattr(self.notifier, "bot", None) is not None:
                await self.notifier.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Error procesando análisis para {symbol}.",
                    parse_mode="Markdown",
                )

    # ======================================================================
    # 🔁 /reactivar <ID>
    # ======================================================================
    async def evaluate_reactivation(self, signal_id: int) -> None:
        """
        Punto de entrada para /reactivar.

        ⚠️ IMPORTANTE:
        - Aquí dejamos una implementación mínima para evitar errores.
        - Más adelante se puede conectar al motor de reactivación avanzado.
        """
        logger.warning(f"⚠️ evaluate_reactivation({signal_id}) aún no implementado.")
        # Podemos aprovechar el notifier para avisar al usuario.
        if getattr(self.notifier, "bot", None) is not None:
            # Por ahora solo avisamos que está pendiente de implementación.
            await self.notifier.bot.send_message(
                chat_id=(
                    self.notifier.chat_id
                    if getattr(self.notifier, "chat_id", None) is not None
                    else signal_id
                ),  # fallback raro, pero evita romper si no hay chat_id
                text=(
                    f"⚠️ La reactivación manual por ID todavía no está implementada.\n"
                    f"ID solicitado: `{signal_id}`"
                ),
                parse_mode="Markdown",
            )

    # ======================================================================
    # 📉 /reanudar y /detener — monitor de posiciones
    # ======================================================================
    async def start_position_monitor(self) -> None:
        """
        Ejecuta una pasada del monitor de posiciones.

        📌 NOTA:
        - El PositionCoordinator actual expone normalmente un método `monitor()`
          que hace un barrido de las posiciones abiertas y envía alertas.
        - No deja un loop infinito; cada llamada es "una ronda" de chequeo.
        """
        if self.position_monitor_running:
            logger.info(
                "🟡 start_position_monitor() llamado pero ya estaba activo (flag)."
            )

        self.position_monitor_running = True

        try:
            # Si en tu PositionCoordinator existe un método monitor(), lo usamos.
            if hasattr(self.position, "monitor"):
                await self.position.monitor()
            else:
                logger.warning(
                    "⚠️ PositionCoordinator no tiene monitor(). Nada que hacer."
                )
        except Exception as e:
            logger.exception(f"❌ Error en start_position_monitor(): {e}")

    async def stop_position_monitor(self) -> None:
        """
        Marca el monitor de posiciones como detenido.

        Si más adelante implementas un loop real en PositionCoordinator, aquí
        podrás cortar ese loop usando este flag.
        """
        if not self.position_monitor_running:
            logger.info(
                "🟡 stop_position_monitor() llamado pero ya estaba detenido (flag)."
            )

        self.position_monitor_running = False
        logger.info("⛔ Monitor de posiciones marcado como detenido.")
