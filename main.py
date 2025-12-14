import asyncio
import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer
from services.telegram_service.telegram_reader import start_telegram_reader
from services.signals_service.signal_reactivation_sync import (
    start_signal_reactivation_loop,
)

logger = logging.getLogger("main")


async def post_init(app):
    # 1️⃣ Crear ApplicationLayer
    app.app_layer = ApplicationLayer(app)

    # 2️⃣ Telegram reader (Telethon)
    asyncio.create_task(start_telegram_reader(app.app_layer))

    # 3️⃣ Reactivation loop ✅ AQUÍ ES DONDE VA
    asyncio.create_task(start_signal_reactivation_loop(app.app_layer, interval_sec=300))

    logger.info("✅ Background tasks iniciadas correctamente")


def main():
    logging.basicConfig(level=logging.INFO)

    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )

    logger.info("🚀 Bot iniciado. Polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
