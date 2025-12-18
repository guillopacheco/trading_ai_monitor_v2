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
            await self.evaluate_signal(signal, context="reactivation")

    # ==============================================================
    # 🚀 ANÁLISIS DE SEÑAL NUEVA
    # ==============================================================
    async def handle_new_signal(self, signal):
        logger.info(f"🧠 Analizando nueva señal {signal['symbol']}")

        result = await self.analysis_service.analyze_symbol(
            symbol=signal["symbol"], direction=signal["direction"], context="entry"
        )

        message = self._format_analysis_message(signal, result)
        await self.notifier.send(message)

        # ==============================================================
        # 🧠 EVALUADOR CENTRAL
        # ==============================================================
        allowed = analysis.get("allowed", False)
        decision = analysis.get("decision")
        score = analysis.get("technical_score")

        # ❌ NO NOTIFICAR si NO reactivó
        if not allowed:
            self.logger.info(
                f"⏳ Señal {symbol} aún no apta: decision={decision}, score={score}"
            )
            return

        # ✅ SOLO AQUÍ hay notificación
        message = (
            "✅ REACTIVADA\n\n"
            f"📊 Análisis de {symbol}\n"
            f"📌 Dirección: {direction.upper()}\n"
            f"🧠 Decisión: {decision}\n"
            f"🎯 Score: {score}\n"
            f"📐 Match: {analysis.get('match_ratio')}%\n"
            f"🏷️ Grade: {analysis.get('grade')}\n"
        )

        if context == "reactivation":
            self.signal_service.mark_signal_reactivated(signal_id)

        await self.notifier.send(message)

        self.logger.info(f"✅ Señal {symbol} REACTIVADA | score={score}")

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

    # dentro de class SignalCoordinator

    async def _notify(self, text: str) -> None:
        if not self.notifier:
            return
        try:
            if hasattr(self.notifier, "safe_send"):
                await self.notifier.safe_send(text)
                return
        except Exception:
            pass
        try:
            if hasattr(self.notifier, "send_message"):
                await self.notifier.safe_send(msg)

                return
        except Exception:
            pass
        try:
            if hasattr(self.notifier, "send"):
                res = self.notifier.send(text)
                if hasattr(res, "__await__"):
                    await res
                return
        except Exception:
            pass
