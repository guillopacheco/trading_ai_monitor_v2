# services/coordinators/signal_coordinator.py
import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    def __init__(self, signal_service, analysis_service, reactivation_engine, notifier):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier
        logger.info("🔧 SignalCoordinator inicializado correctamente.")

    def get_pending_signals(self, limit=None):
        # ✅ tolera service con o sin limit
        try:
            if limit is None:
                return self.signal_service.get_pending_signals()
            return self.signal_service.get_pending_signals(limit)
        except TypeError:
            return self.signal_service.get_pending_signals()

    async def auto_reactivate(self, limit=10):
        pending = self.get_pending_signals(limit) or []
        logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for s in pending:
            try:
                signal_id = s.get("id") or s.get("signal_id")
                symbol = s.get("symbol")
                direction = s.get("direction")

                logger.info(
                    f"🔍 Reactivación eval → {symbol} {direction} (ID={signal_id})"
                )

                analysis = await self.analysis_service.analyze_symbol(
                    symbol, direction, context="reactivation"
                )

                result = await self.reactivation_engine.evaluate_signal(
                    symbol, direction, analysis
                )

                if result.get("allowed"):
                    # marca reactivada (si existe)
                    try:
                        self.signal_service.mark_signal_reactivated(signal_id)
                    except Exception:
                        try:
                            self.signal_service.mark_signal_as_reactivated(signal_id)
                        except Exception:
                            pass

                    msg = f"♻️ Señal REACTIVADA ✅\n{symbol} {direction}\nID={signal_id}\n{result.get('reason','')}"
                    logger.info(msg)
                    try:
                        await self.notifier.send_message(msg)
                    except Exception:
                        pass
                else:
                    reason = result.get("reason") or "No apta"
                    logger.info(f"⏳ Señal {signal_id} aún no apta: {reason}")

            except Exception as e:
                logger.exception(
                    f"❌ Error evaluando reactivación ID={s.get('id')}: {e}"
                )
