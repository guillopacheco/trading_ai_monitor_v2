# services/coordinators/signal_coordinator.py
import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    def __init__(self, signal_service, analysis_service, reactivation_engine, notifier):
        self.signal_service = signal_service
        self.analysis = analysis_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier
        logger.info("🔧 SignalCoordinator inicializado correctamente.")

    def get_pending_signals(self):
        # Firma REAL (sin argumentos)
        return self.signal_service.get_pending_signals()

    async def auto_reactivate(self):
        pending = self.get_pending_signals() or []
        logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for s in pending:
            try:
                signal_id = s["id"]
                symbol = s["symbol"]
                direction = s["direction"]

                logger.info(
                    f"🔍 Reactivación eval → {symbol} {direction} (ID={signal_id})"
                )

                analysis = await self.analysis.analyze_symbol(
                    symbol, direction, context="reactivation"
                )

                decision = await self.reactivation_engine.evaluate_signal(
                    symbol, direction, analysis
                )

                if decision.get("allowed"):
                    self.signal_service.mark_signal_reactivated(signal_id)

                    await self.notifier.send_message(
                        f"♻️ Señal reactivada\n"
                        f"{symbol} {direction}\n"
                        f"{decision.get('reason', '')}"
                    )

                    logger.info(f"✅ Señal reactivada ID={signal_id}")
                else:
                    logger.info(
                        f"⏳ Señal {signal_id} aún no apta: {decision.get('reason')}"
                    )

            except Exception as e:
                logger.exception(f"❌ Error evaluando reactivación ID={s}: {e}")
