import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    def __init__(
        self,
        signal_service,
        analysis_service,
        notifier,
        technical_engine,
        reactivation_engine,
    ):
        self.signal_service = signal_service
        self.analysis_service = analysis_service
        self.notifier = notifier
        self.engine = technical_engine
        self.reactivation_engine = reactivation_engine

        logger.info("🔧 SignalCoordinator inicializado correctamente.")

    # ---------------------------------------------------------
    # NUEVA SEÑAL
    # ---------------------------------------------------------
    async def process_new_signal(self, signal):
        """
        Maneja una señal recién llegada del canal VIP.
        """
        logger.info(f"📥 Nueva señal recibida | {signal.symbol} {signal.direction}")

        # Guardar en la base de datos
        self.signal_service.save_signal(signal)

        # Analizar inmediatamente (contexto = 'entry')
        analysis = await self.technical_engine.analyze(
            signal.symbol, signal.direction, context="entry"
        )

        # Guardar log del análisis
        self.signal_service.save_analysis_log(signal.id, analysis)

        # Notificar al usuario
        await self.notifier.safe_send(
            f"📊 *Nueva señal analizada: {signal.symbol}*\n"
            f"Dirección: *{signal.direction}*\n"
            f"Decisión: `{analysis['decision']}`\n"
            f"Confianza: *{analysis['confidence']}*\n"
        )

    # ---------------------------------------------------------
    # REACTIVACIÓN AVANZADA
    # ---------------------------------------------------------
    async def evaluate_reactivation(self, signal):
        """
        Evalúa si una señal ignorada debe reactivarse.
        Usa ReactivationEngine.
        """
        logger.info(f"♻️ Evaluando reactivación para ID={signal.id}")

        result = await self.reactivation_engine.evaluate(signal)

        # Guardamos trace
        self.signal_service.save_reactivation_state(
            signal.id, result.state, result.to_dict()
        )

        # Notificación
        await self.notifier.safe_send(result.to_telegram_message())

        return result

        async def auto_reactivate(self):
            """
            Revisa señales pendientes de reactivación y aplica la lógica avanzada.
            """

            pending = self.signal_service.get_pending_signals()
            if not pending:
                return

            for signal in pending:
                try:
                    signal_id = signal["id"]
                    symbol = signal["symbol"]
                    direction = signal["direction"]

                    # 1. Ejecutar análisis técnico completo
                    analysis = await self.engine.run(
                        symbol, direction, context="reactivation"
                    )

                    # 2. Lógica de decisión avanzada
                    decision = (
                        self.reactivation_engine.evaluate_signal_for_reactivation(
                            signal, analysis
                        )
                    )

                    # 3. Guardar resultado
                    self.signal_service.update_reactivation_status(
                        signal_id, decision, analysis
                    )

                    # 4. Notificación
                    await self.notifier.safe_send(
                        f"🔄 Reactivación {symbol}: *{decision}*"
                    )

                except Exception as e:
                    logger.exception(
                        f"❌ Error evaluando reactivación ID={signal_id}: {e}"
                    )
                    await self.notifier.safe_send(
                        f"❌ Error procesando reactivación de {symbol}"
                    )
