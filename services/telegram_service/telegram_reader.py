# services/telegram_service/telegram_reader.py

import logging
from telethon import TelegramClient, events

from config import API_ID, API_HASH, TELEGRAM_SESSION, SIGNAL_SOURCE_CHANNEL
from services.application.signal_service import SignalService

logger = logging.getLogger("telegram_reader")

signal_service = SignalService()


async def start_telegram_reader(app_layer):
    """
    Inicia el lector de señales del canal VIP.
    """
    logger.info("📡 Lector de señales — inicializando cliente Telethon...")

    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)

    @client.on(events.NewMessage(chats=[SIGNAL_SOURCE_CHANNEL]))
    async def handler(event):
        """
        Maneja mensajes nuevos del canal VIP.
        """
        text = event.message.message
        logger.info(f"📩 Señal recibida: {text}")

        try:
            result = await signal_service.process_incoming_signal(text)
            if result:
                logger.info(f"📥 Señal procesada correctamente: {result}")

                # Notificar a ApplicationLayer → para ejecutar análisis inicial si aplica
                if hasattr(app_layer, "signal"):
                    await app_layer.signal.handle_new_signal(result)

        except Exception as e:
            logger.exception(f"❌ Error procesando señal: {e}")

    await client.start()
    logger.info("📡 Lector de señales activo y escuchando canal VIP.")

    # Ejecutar de manera no bloqueante
    client.loop.run_in_executor(None, client.run_until_disconnected)
