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

    def get_pending_signals(self, limit: int = 10):
        # SignalService debe exponer get_pending_signals(limit=...)
        return self.signal_service.get_pending_signals(limit=limit)

    async def auto_reactivate(self, limit: int = 10):
        pending = self.get_pending_signals(limit=limit) or []
        logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for s in pending:
            # soporta dict o tuplas según implementación real
            try:
                signal_id = s["id"] if isinstance(s, dict) else s[0]
                symbol = s["symbol"] if isinstance(s, dict) else s[1]
                direction = s["direction"] if isinstance(s, dict) else s[2]
            except Exception:
                logger.exception("❌ Formato inválido de señal pendiente: %r", s)
                continue

            try:
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
                    # Marca reactivada (nombre real según tu SignalService)
                    try:
                        self.signal_service.mark_signal_reactivated(signal_id)
                    except Exception:
                        # fallback por si el nombre real es otro
                        try:
                            self.signal_service.mark_signal_as_reactivated(signal_id)
                        except Exception:
                            logger.exception(
                                "❌ No pude marcar señal como reactivada (ID=%s)",
                                signal_id,
                            )

                    msg = (
                        f"♻️ **Señal reactivada**\n"
                        f"📌 {symbol} ({direction})\n"
                        f"✅ {decision.get('reason', 'Apta por reactivación')}"
                    )
                    try:
                        await self.notifier.send_message(msg)
                    except Exception:
                        logger.exception(
                            "⚠️ Falló envío de notificación reactivación (ID=%s)",
                            signal_id,
                        )

                    logger.info(f"✅ Señal reactivada ID={signal_id}")

                else:
                    reason = decision.get("reason", "No cumple criterios")
                    logger.info(f"⏳ Señal aún no apta ID={signal_id} → {reason}")

            except Exception as e:
                logger.exception(
                    "❌ Error evaluando reactivación ID=%s: %s", signal_id, e
                )
