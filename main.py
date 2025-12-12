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

    # 1️⃣ Crear bot Telegram
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 2️⃣ Crear capa de aplicación con el bot
    app_layer = ApplicationLayer(bot_app.bot)

    # 3️⃣ Crear CommandBot
    command_bot = CommandBot(app_layer, bot_app)

    # 4️⃣ Iniciar Telegram reader
    asyncio.create_task(start_telegram_reader(app_layer))

    # 5️⃣ Iniciar monitor de reactivación
    asyncio.create_task(start_reactivation_monitor(app_layer))

    # 6️⃣ Iniciar CommandBot (polling)
    await bot_app.run_polling(close_loop=False)

    logger.info("✔ Sistema ejecutándose.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        raise
