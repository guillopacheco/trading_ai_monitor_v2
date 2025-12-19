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
    # 🚀 NUEVA SEÑAL
    # ==============================================================
    async def handle_new_signal(self, signal: dict):
        await self.evaluate_signal(signal, context="entry")

    # ==============================================================
    # 🔁 AUTO REACTIVACIÓN
    # ==============================================================
    async def auto_reactivate(self, limit: int = 10):
        pending = self.signal_service.get_pending_signals(limit=limit) or []

        if not pending:
            logger.info("📭 No hay señales pendientes.")
            return

        for signal in pending:
            await self.evaluate_signal(signal, context="reactivation")

    # ==============================================================
    # 🧠 MÉTODO ÚNICO CENTRAL
    # ==============================================================
    async def evaluate_signal(self, signal: dict, context: str):
        symbol = signal["symbol"]
        direction = signal["direction"]

        logger.info(f"🔍 Evaluando {symbol} | contexto={context}")

        analysis = await self.analysis_service.analyze_symbol(
            symbol=symbol,
            direction=direction,
            context=context,
        )

        allowed = analysis.get("allowed", False)

        # ❌ FILTRO CRÍTICO (Commit 4)
        if context == "reactivation" and not allowed:
            logger.info(f"⏳ Señal {symbol} aún no apta para reactivar")
            return

        # ----------------------------------------------------------
        # 📩 MENSAJE
        # ----------------------------------------------------------
        header = "♻️ REACTIVADA" if context == "reactivation" else "🚀 ANÁLISIS SEÑAL"

        message = (
            f"{header}\n\n"
            f"📊 {symbol}\n"
            f"📌 Dirección: {direction.upper()}\n"
            f"🧠 Decisión: {analysis.get('decision')}\n"
            f"🎯 Score: {analysis.get('technical_score')}\n"
            f"📐 Match: {analysis.get('match_ratio')}%\n"
            f"🏷️ Grade: {analysis.get('grade')}\n"
        )

        if context == "reactivation":
            self.signal_service.mark_reactivated(signal["id"])

        await self.notifier.send(message)
