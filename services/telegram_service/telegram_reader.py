import logging
from telethon import TelegramClient, events

from config import API_ID, API_HASH, TELEGRAM_SESSION, TELEGRAM_CHANNEL_ID

from services.application.signal_service import SignalService

telegram_reader_logger = logging.getLogger("telegram_reader")


async def start_telegram_reader(app_layer):
    """
    Lector de señales del canal VIP.
    Corre dentro del loop principal (sin hilos).
    """

    signal_service = SignalService()

    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)

    await client.start()
    telegram_reader_logger.info("📡 Lector de señales — cliente iniciado.")

    # -------------------------------
    #   Capturar mensajes entrantes
    # -------------------------------
    @client.on(events.NewMessage(chats=[TELEGRAM_CHANNEL_ID]))
    async def handler(event):
        text = event.raw_text.strip()
        telegram_reader_logger.info(f"📨 Señal recibida del canal: {text}")

        # Parseo simple de formato: "#BTC/USDT (Long)"
        try:
            parts = text.split()
            symbol = parts[0].replace("#", "").replace("/", "")
            direction = "long" if "long" in text.lower() else "short"
        except:
            telegram_reader_logger.warning("⚠️ No fue posible parsear la señal.")
            return

        signal_service.process_incoming_signal(symbol, direction)

        telegram_reader_logger.info(
            f"💾 Señal procesada: {symbol} ({direction})"
        )

    telegram_reader_logger.info("📡 Lector de señales activo y escuchando...")

    # Mantener conexión viva dentro del loop principal
    await client.run_until_disconnected()
