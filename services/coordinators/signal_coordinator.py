# services/coordinators/signal_coordinator.py
import logging

logger = logging.getLogger("signal_coordinator")


import logging


import logging


class SignalCoordinator:
    def __init__(self, signal_service, analysis_service, reactivation_engine, notifier):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier

        # ✅ B2: evita el crash por self.logger inexistente
        self.logger = logger

    def get_pending_signals(self, limit: int = 10):
        """
        Devuelve señales pendientes. Compatible con SignalService con o sin parámetro `limit`.
        """
        try:
            # si el service soporta limit
            pending = self.signal_service.get_pending_signals(limit=limit)
        except TypeError:
            # si el service NO soporta limit
            pending = self.signal_service.get_pending_signals()

        pending = pending or []
        if limit:
            pending = pending[:limit]
        return pending

    def get_pending_count(self):
        return len(self.signal_service.get_pending_signals())

    def is_running(self):
        return True  # luego lo conectamos al flag real

    async def auto_reactivate(self, limit: int = 10):
        pending = self.get_pending_signals(limit=limit)
        self.logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for sig in pending:
            try:
                signal_id = sig.get("id")
                symbol = sig.get("symbol")
                direction = sig.get("direction")

                if not symbol or not direction:
                    self.logger.warning(f"⚠️ Señal inválida (ID={signal_id}): {sig}")
                    continue

                self.logger.info(
                    f"🔍 Reactivación eval → {symbol} {direction} (ID={signal_id})"
                )

                analysis = await self.analysis_service.analyze_symbol(
                    symbol=symbol,
                    direction=direction,
                    context="reactivation",
                )

                if not analysis:
                    self.logger.info(
                        f"⏳ Señal {signal_id} aún no apta: análisis vacío"
                    )
                    continue

                if analysis.get("allowed"):
                    self.logger.info(f"✅ Señal {signal_id} REACTIVADA ({symbol})")
                    self.signal_service.mark_signal_reactivated(signal_id)
                else:
                    self.logger.info(
                        f"⏳ Señal {signal_id} aún no apta: "
                        f"decision={analysis.get('decision')}, "
                        f"score={analysis.get('technical_score')}, "
                        f"match={analysis.get('match_ratio')}, "
                        f"grade={analysis.get('grade')}"
                    )

            except Exception as e:
                self.logger.exception(
                    f"❌ Error evaluando reactivación ID={sig.get('id')}: {e}"
                )
