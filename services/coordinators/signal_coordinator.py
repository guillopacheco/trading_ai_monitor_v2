"""
SignalCoordinator
-----------------
Coordina señales entrantes, reactivación y notificaciones.
GARANTÍA: toda señal analizada genera mensaje a Telegram.
"""

import logging
from typing import Optional

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    def __init__(self, signal_service, analysis_service, reactivation_engine, notifier):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier

        self.logger = logger
        self.logger.info("🔧 SignalCoordinator inicializado correctamente.")

    # ==============================================================
    # 🔁 AUTO REACTIVACIÓN
    # ==============================================================
    async def auto_reactivate(self, limit: int = 10):
        """Evalúa señales pendientes y decide reactivación."""
        pending = self.signal_service.get_pending_signals(limit=limit) or []

        if not pending:
            self.logger.info("📭 No hay señales pendientes para reactivación.")
            return

        self.logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for signal in pending:
            await self._evaluate_signal(signal, context="reactivation")

    # ==============================================================
    # 🚀 ANÁLISIS DE SEÑAL NUEVA
    # ==============================================================
    async def analyze_new_signal(self, signal: dict):
        """Analiza una señal recién recibida."""
        await self._evaluate_signal(signal, context="entry")

    # ==============================================================
    # 🧠 EVALUADOR CENTRAL
    # ==============================================================
    async def _evaluate_signal(self, signal: dict, context: str):
        """Evalúa señal y notifica SIEMPRE."""
        signal_id = signal.get("id")
        symbol = signal.get("symbol")
        direction = signal.get("direction")

        self.logger.info(f"🔍 Evaluando señal {symbol} {direction} (ID={signal_id})")

        try:
            analysis = await self.analysis_service.analyze_symbol(
                symbol=symbol,
                direction=direction,
                context=context,
            )
        except Exception as e:
            self.logger.exception(f"❌ Error analizando {symbol}: {e}")
            await self.notifier.send_message(f"❌ Error analizando {symbol}\n{str(e)}")
            return

        # ----------------------------------------------------------
        # 📩 CONSTRUIR MENSAJE
        # ----------------------------------------------------------
        context_label = "♻️ REACTIVACIÓN" if context == "reactivation" else "🚀 ENTRADA"

        message = (
            f"{context_label}\n"
            f"📊 Análisis de {symbol}\n"
            f"📌 Dirección: {direction.upper()}\n"
            f"🧠 Decisión: {analysis.get('decision')}\n"
            f"🎯 Score: {analysis.get('technical_score')}\n"
            f"📐 Match: {analysis.get('match_ratio')}%\n"
            f"🏷️ Grade: {analysis.get('grade')}\n"
        )

        # ----------------------------------------------------------
        # ✅ / ⏳ ACCIÓN
        # ----------------------------------------------------------
        if analysis.get("allowed"):
            message = "✅ REACTIVADA\n\n" + message

            if context == "reactivation":
                self.signal_service.mark_signal_reactivated(signal_id)

        else:
            message = "⏳ NO APTA (monitorizando)\n\n" + message

        # ----------------------------------------------------------
        # 📤 ENVÍO GARANTIZADO
        # ----------------------------------------------------------
        await self.notifier.safe_send(message)

        self.logger.info(
            f"📨 Notificado {symbol}: decision={analysis.get('decision')} | score={analysis.get('technical_score')}"
        )
