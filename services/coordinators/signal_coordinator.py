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
        self.engine = technical_engine  # Motor técnico correcto
        self.reactivation_engine = reactivation_engine

        logger.info("🔧 SignalCoordinator inicializado correctamente.")

    # ---------------------------------------------------------
    # 1) PROCESAR SEÑAL RECIÉN LLEGADA
    # ---------------------------------------------------------
    async def process_new_signal(self, signal):
        logger.info(f"📥 Nueva señal | {signal.symbol} {signal.direction}")

        # Guardar la señal
        self.signal_service.save_signal(signal)

        # Analizar entrada
        analysis = await self.engine.analyze(
            signal.symbol, signal.direction, context="entry"
        )

        # Guardar trace del análisis
        self.signal_service.save_analysis_log(signal.id, analysis)

        # Notificación en Telegram
        await self.notifier.safe_send(
            f"📊 *Nueva señal: {signal.symbol}*\n"
            f"Dirección: *{signal.direction}*\n"
            f"Decisión: `{analysis['decision']}`\n"
            f"Confianza: *{analysis['confidence']}*"
        )

    # ---------------------------------------------------------
    # 2) EVALUAR UNA SEÑAL INDIVIDUAL PARA REACTIVACIÓN
    # ---------------------------------------------------------
    async def evaluate_reactivation(self, signal):
        logger.info(f"♻️ Reactivación manual ID={signal.id}")

        result = await self.reactivation_engine.evaluate(signal)

        self.signal_service.save_reactivation_state(
            signal.id, result.state, result.to_dict()
        )

        await self.notifier.safe_send(result.to_telegram_message())

        return result

    # ---------------------------------------------------------
    # 3) AUTO-REACTIVACIÓN INTELIGENTE
    # ---------------------------------------------------------
    async def auto_reactivate(self):
        """
        Revisa señales pendientes y decide si reactivarlas.
        """
        pending = self.signal_service.get_pending_signals()
        if not pending:
            return

        logger.info(f"🔄 {len(pending)} señales pendientes para reactivación.")

        for s in pending:
            try:
                signal_id = s["id"]
                symbol = s["symbol"]
                direction = s["direction"]

                logger.info(f"🔍 Evaluando reactivación | ID={signal_id} {symbol}")

                # 1. Análisis técnico actual
                analysis = await self.engine.analyze(
                    symbol, direction, context="reactivation"
                )

                # 2. Decisión táctica de reactivación
                decision = await self.reactivation_engine.evaluate_dict_signal(
                    s, analysis
                )

                # 3. Guardar decisión
                self.signal_service.update_reactivation_status(
                    signal_id, decision, analysis
                )

                # 4. Notificación
                await self.notifier.safe_send(f"🔄 Reactivación {symbol}: *{decision}*")

            except Exception as e:
                logger.exception(f"❌ Error en reactivación ID={signal_id}: {e}")
                await self.notifier.safe_send(
                    f"❌ Error procesando reactivación de {symbol}"
                )
