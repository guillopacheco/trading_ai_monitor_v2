import asyncio
import logging

logger = logging.getLogger("signal_reactivation_sync")


async def start_signal_reactivation_loop(app_layer, interval_sec=300):
    """
    Revisa señales ignoradas cada X segundos
    y evalúa si deben reactivarse.
    """

    logger.info("♻️ Monitor automático de reactivación iniciado")

    while True:
        try:
            pending_signals = app_layer.signal.get_pending_signals()

            for signal in pending_signals:
                symbol = signal["symbol"]
                direction = signal["direction"]
                signal_id = signal["id"]

                analysis = await app_layer.analysis.analyze_symbol(
                    symbol, direction, context="reactivation"
                )

                result = await app_layer.reactivation_engine.evaluate_signal(
                    symbol, direction, analysis
                )

                if result.get("allowed"):
                    logger.info(f"♻️ Reactivando señal {signal_id} ({symbol})")

                    app_layer.signal.mark_signal_reactivated(signal_id)

                    # Mensaje Telegram (usa el mismo formato)
                    message = (
                        "♻️ *SEÑAL REACTIVADA*\n\n"
                        f"Par: {symbol}\n"
                        f"Dirección: {direction.upper()}\n"
                        f"Motivo: {result.get('reason')}\n"
                        f"Score: {analysis.get('technical_score')}\n"
                        f"Match: {analysis.get('match_ratio')}\n"
                        f"Grade: {analysis.get('grade')}"
                    )

                    await app_layer.notifier.send_message(message)

        except Exception as e:
            logger.exception(f"❌ Error en loop de reactivación: {e}")

        await asyncio.sleep(interval_sec)
