# services/coordinators/signal_coordinator.py

import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    """
    Coordina:
    - /analizar (manual)
    - auto_reactivate (background)
    """

    def __init__(self, signal_service, analysis_service, reactivation_engine, notifier):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier

        logger.info("🔧 SignalCoordinator inicializado correctamente.")

    # ==================================================================
    # /analizar SYMBOL DIRECTION
    # ==================================================================
    async def manual_analyze_request(self, symbol: str, direction: str):
        try:
            analysis = await self.analysis_service.analyze_symbol(
                symbol=symbol,
                direction=direction,
                context="entry",
            )

            txt = self.analysis_service.format_for_telegram(
                symbol=symbol,
                direction=direction,
                result=analysis,
                context="entry",
            )
            await self.notifier.safe_send(txt)
            return txt

        except Exception as e:
            logger.exception(f"❌ Error en análisis manual {symbol} {direction}: {e}")
            msg = f"❌ Error analizando {symbol} ({direction})."
            await self.notifier.safe_send(msg)
            return msg

    # ==================================================================
    # AUTO-REACTIVACIÓN (background)
    # ==================================================================
    async def auto_reactivate(self):
        pending = self.signal_service.get_pending_signals()

        if not pending:
            return

        logger.info(f"🔁 Auto-reactivación: {len(pending)} señales pendientes.")

        for sig in pending:
            signal_id = sig.get("id", "?")
            symbol = sig.get("symbol")
            direction = sig.get("direction")

            if not symbol or not direction:
                continue

            try:
                logger.info(
                    f"🔍 Reactivación eval → {symbol} {direction} (ID={signal_id})"
                )

                analysis = await self.analysis_service.analyze_symbol(
                    symbol=symbol,
                    direction=direction,
                    context="reactivation",
                )

                decision = await self.reactivation_engine.evaluate_signal(
                    symbol=symbol,
                    direction=direction,
                    analysis=analysis,
                )

                # Guardar evento si existe el método (no revienta si no está)
                if hasattr(self.signal_service, "save_reactivation_event"):
                    self.signal_service.save_reactivation_event(
                        signal_id=signal_id,
                        status="allowed" if decision.get("allowed") else "blocked",
                        details=decision,
                    )

                if decision.get("allowed"):
                    if hasattr(self.signal_service, "mark_reactivated"):
                        self.signal_service.mark_reactivated(signal_id)

                    msg = (
                        f"⚡ *Reactivación permitida* para {symbol} "
                        f"({direction})\n"
                        f"📌 {decision.get('reason')}"
                    )
                    await self.notifier.safe_send(msg)
                else:
                    logger.info(
                        f"⏳ Señal {signal_id} aún no apta: {decision.get('reason')}"
                    )

            except Exception as e:
                logger.exception(f"❌ Error evaluando reactivación ID={signal_id}: {e}")
