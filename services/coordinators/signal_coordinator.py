import logging

logger = logging.getLogger("signal_coordinator")


class SignalCoordinator:
    """
    Coordina acciones relacionadas con señales:

      • guardar señales nuevas
      • registrar análisis
      • interactuar con ReactivationEngine
      • notificar resultados
    """

    def __init__(self, signal_service, notifier, reactivation_engine):
        self.signal_service = signal_service
        self.notifier = notifier
        self.reactivation_engine = reactivation_engine

    # ---------------------------------------------------------
    # REGISTRO DE SEÑALES
    # ---------------------------------------------------------
    async def save_signal(self, symbol: str, direction: str, entry_price: float):
        """
        Guarda una señal recién recibida desde telegram_reader.
        (Se usa cuando llegan señales del canal VIP)
        """
        try:
            signal_id = self.signal_service.save_signal(symbol, direction, entry_price)
            logger.info(f"📌 Señal registrada: ID={signal_id} {symbol} {direction}")
            return signal_id
        except Exception as e:
            logger.error(f"❌ Error guardando señal: {e}", exc_info=True)

    # ---------------------------------------------------------
    # EVALUACIÓN / REACTIVACIÓN MANUAL
    # ---------------------------------------------------------
    async def evaluate_for_reactivation(self, signal):
        """
        Evalúa si una señal puede ser reactivada (modo manual).
        """
        symbol = signal["symbol"]
        direction = signal["direction"]

        logger.info(f"🔎 Reactivación manual solicitada: {symbol} {direction}")

        try:
            result = await self.reactivation_engine.evaluate_signal(symbol, direction)

            text = (
                f"📌 *Reactivación manual*\n"
                f"Par: *{symbol}*\n"
                f"Dirección: *{direction}*\n"
                f"Resultado: `{result['reason']}`"
            )
            await self.notifier.safe_send(text)

            return result
        except Exception as e:
            logger.error(f"❌ Error evaluando reactivación manual: {e}", exc_info=True)
            await self.notifier.safe_send("❌ Error interno evaluando reactivación.")
            return None
