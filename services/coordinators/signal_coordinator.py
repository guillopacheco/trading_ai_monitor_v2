import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    """
    Coordina:
    - Nuevas señales recibidas
    - Reactivación avanzada
    """

    def __init__(self, signal_service, reactivation_engine, notifier, technical_engine):
        self.signal_service = signal_service
        self.reactivation_engine = reactivation_engine
        self.notifier = notifier
        self.technical_engine = technical_engine

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
