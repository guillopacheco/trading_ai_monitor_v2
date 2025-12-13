import asyncio
import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer
from services.telegram_service.command_bot import CommandBot
from services.telegram_service.telegram_reader import start_telegram_reader
from services.signals_service.signal_reactivation_sync import start_reactivation_monitor

logger = logging.getLogger("main")


async def main():
    logger.info("🚀 Trading AI Monitor iniciando...")

    # 1️⃣ Crear aplicación Telegram
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 2️⃣ Crear ApplicationLayer (UNA SOLA VEZ)
    app_layer = ApplicationLayer(application.bot)

    # 3️⃣ CommandBot
    command_bot = CommandBot(application, app_layer)
    command_bot.register_handlers()

    # 4️⃣ Lectura de señales
    asyncio.create_task(start_telegram_reader(app_layer))

    # 5️⃣ Reactivación automática
    asyncio.create_task(start_reactivation_monitor(app_layer))

    # 6️⃣ Iniciar polling (NO usar asyncio.run aquí)
    application.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception("❌ Error crítico en main")
        raise
