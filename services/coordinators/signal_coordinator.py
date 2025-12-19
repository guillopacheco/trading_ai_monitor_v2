import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    def __init__(self, signal_service, analysis_service, reactivation_engine, notifier):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier

        logger.info("🔧 SignalCoordinator inicializado correctamente.")

    # ==============================================================
    # 🔁 AUTO REACTIVACIÓN
    # ==============================================================
    async def auto_reactivate(self, limit: int = 10):
        pending = self.signal_service.get_pending_signals(limit=limit) or []

        if not pending:
            logger.info("📭 No hay señales pendientes para reactivación.")
            return

        logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for signal in pending:
            await self.evaluate_signal(signal, context="reactivation")

    # ==============================================================
    # 🚀 NUEVA SEÑAL
    # ==============================================================
    async def _evaluate_signal(self, signal, context):
        await self.evaluate_signal(signal, context="entry")

    # ==============================================================
    # 🧠 EVALUADOR CENTRAL (ÚNICO)
    # ==============================================================
    async def _evaluate_signal(self, signal, context):
        symbol = signal["symbol"]
        direction = signal["direction"]

        logger.info(f"🔍 Evaluando señal {symbol} ({context})")

        analysis = await self.analysis_service.analyze_symbol(
            symbol=symbol,
            direction=direction,
            context=context,
        )

        allowed = analysis.get("allowed", False)
        decision = analysis.get("decision")
        score = analysis.get("technical_score")

        # ----------------------------------------------------------
        # ❌ NO NOTIFICAR si NO reactivó
        # ----------------------------------------------------------
        if context == "reactivation" and not allowed:
            logger.info(
                f"⏳ Señal {symbol} aún no apta: decision={decision}, score={score}"
            )
            return

        # ----------------------------------------------------------
        # 📩 CONSTRUIR MENSAJE
        # ----------------------------------------------------------
        header = "♻️ REACTIVADA" if context == "reactivation" else "🚀 ANÁLISIS SEÑAL"

        message = (
            f"{header}\n\n"
            f"📊 {symbol}\n"
            f"📌 Dirección: {direction.upper()}\n"
            f"🧠 Decisión: {decision}\n"
            f"🎯 Score: {score}\n"
            f"📐 Match: {analysis.get('match_ratio')}%\n"
            f"🏷️ Grade: {analysis.get('grade')}\n"
        )

        # ----------------------------------------------------------
        # ✅ MARCAR REACTIVACIÓN
        # ----------------------------------------------------------
        if context == "reactivation":
            self.signal_service.mark_signal_reactivated(signal["id"])

        # ----------------------------------------------------------
        # 📤 ENVÍO
        # ----------------------------------------------------------
        await self.notifier.send(message)

        logger.info(f"📨 Notificado {symbol}: decision={decision} | score={score}")

        def is_running(self) -> bool: