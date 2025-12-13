import logging
from typing import Any

from services.application.analysis_service import AnalysisService
from services.application.operation_service import OperationService
from services.application.signal_service import SignalService

from services.coordinators.signal_coordinator import SignalCoordinator

# El coordinador de posiciones se dejará para una fase posterior
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

    SignalCoordinator espera:

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

    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier

        # -----------------------------
        # Servicios base
        # -----------------------------
        self.analysis_service = AnalysisService()
        self.signal_service = SignalService()
        self.operation_service = OperationService(notifier)

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
            self.signal_service,
            self.reactivation_engine,
            self.notifier,
            self.technical_engine,
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
        # 1) Ejecutar análisis
        try:
            # Versión actual de AnalysisService (async)
            result: dict = await self.analysis_service.analyze_symbol(symbol, direction)
        except (AttributeError, TypeError):
            # Fallback por si AnalysisService usa otro nombre
            result = _technical_engine_module.analyze(
                symbol,
                direction_hint=direction,
                context="entry",
            )

        # 2) Formatear mensaje
        try:
            # Si existe un formateador dedicado, úsalo
            from services.application.analysis_service import (
                format_analysis_for_telegram,
            )

            text = format_analysis_for_telegram(symbol, direction, result)
        except Exception:
            # Fallback genérico
            decision = result.get("decision", "-")
            score = result.get("technical_score", 0)
            match_ratio = result.get("match_ratio", 0)
            confidence = result.get("confidence", 0)
            grade = result.get("grade", "-")
            reasons = result.get("decision_reasons", [])

            lines = [
                f"📊 *Análisis de {symbol}*",
                "🧭 Contexto: *Entrada*",
                "",
                f"🔴 *Decisión:* `{decision}`",
                f"📈 *Score técnico:* {score} / 100",
                f"🎯 *Match técnico:* {match_ratio} %",
                f"🔎 *Confianza:* {confidence * 100:.0f} %",
                f"🏅 *Grade:* {grade}",
            ]
            if reasons:
                lines.append("")
                lines.append("📌 *Motivos:*")
                for r in reasons:
                    lines.append(f"• {r}")
            text = "\n".join(lines)

        # 3) Enviar a Telegram
        await self.notifier.safe_send(text, chat_id=chat_id)
        return result

    async def evaluate_reactivation(self, signal_id: int) -> Any:
        """
        Reactivación manual de una señal concreta (comando /reactivar).
        """
        # 1) Cargar señal
        try:
            signal = self.signal_service.get_signal_by_id(signal_id)
        except Exception as e:
            logger.error(
                f"❌ Error obteniendo señal ID={signal_id}: {e}", exc_info=True
            )
            await self.notifier.safe_send(
                f"❌ No se pudo cargar la señal ID={signal_id}",
                chat_id=None,
            )
            return None

        if not signal:
            await self.notifier.safe_send(
                f"⚠️ Señal ID={signal_id} no encontrada o ya cerrada.",
                chat_id=None,
            )
            return None

        # 2) Delegar en el reactivation engine vía SignalCoordinator
        try:
            result = await self.signal.evaluate_reactivation(signal)
            return result
        except Exception as e:
            logger.error(
                f"❌ Error evaluando reactivación ID={signal_id}: {e}",
                exc_info=True,
            )
            await self.notifier.safe_send(
                f"❌ Error evaluando reactivación de la señal {signal_id}",
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
