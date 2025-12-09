import logging
from telethon import TelegramClient, events

from config import API_ID, API_HASH, TELEGRAM_SESSION, TELEGRAM_CHANNEL_ID

telegram_reader_logger = logging.getLogger("telegram_reader")


# ===================================================================
#   TELEGRAM READER — Lector oficial de señales del canal VIP
# ===================================================================
async def start_telegram_reader(app_layer):
    """
    Lector de señales usando Telethon.
    • Corre en el loop principal (sin threads)
    • Cada mensaje recibido se envía al SignalCoordinator
    """

    if not hasattr(app_layer, "signal"):
        telegram_reader_logger.error("❌ ApplicationLayer no tiene signal coordinator.")
        return

    signal_coord = app_layer.signal  # SignalCoordinator

    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)

    await client.start()
    telegram_reader_logger.info("📡 Cliente Telethon conectado y listo para escuchar señales...")

    # ------------------------------------------------------------------
    #  Handler de señales nuevas
    # ------------------------------------------------------------------
    @client.on(events.NewMessage(chats=[TELEGRAM_CHANNEL_ID]))
    async def handler(event):
        text = event.raw_text.strip()
        telegram_reader_logger.info(f"📨 Señal recibida del canal VIP: {text}")

        # Intentar extraer símbolo
        try:
            parts = text.split()
            raw_symbol = parts[0].replace("#", "").replace("/", "").upper()
        except Exception:
            telegram_reader_logger.error("❌ No se pudo extraer el símbolo de la señal.")
            return

        # Detectar dirección
        text_l = text.lower()
        if "long" in text_l:
            direction = "long"
        elif "short" in text_l:
            direction = "short"
        else:
            telegram_reader_logger.warning("⚠️ No se encontró LONG o SHORT en la señal.")
            return

        # ------------------------------------------------------------------
        #  Enviar señal al COORDINADOR para que:
        #  • Se registre
        #  • Se analice con AnalysisService
        #  • Se guarde el log
        #  • Se notifique con Notifier
        # ------------------------------------------------------------------
        try:
            await signal_coord.process_telegram_signal(
                symbol=raw_symbol,
                direction=direction,
                raw_text=text
            )

            telegram_reader_logger.info(
                f"💾 Señal enviada al SignalCoordinator → {raw_symbol} ({direction})"
            )

        except Exception as e:
            telegram_reader_logger.error(f"❌ Error procesando señal: {e}", exc_info=True)

    telegram_reader_logger.info("📡 Escuchando canal VIP...")

    # Mantener sesión activa
    await client.run_until_disconnected()
