import asyncio
import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer
from services.telegram_service.telegram_reader import start_telegram_reader

logger = logging.getLogger("main")


async def post_init(app):
    app.app_layer = ApplicationLayer(app)
    asyncio.create_task(start_telegram_reader(app.app_layer))
    logger.info("✅ Background tasks iniciadas correctamente")


from services.reactivation_engine.signal_reactivation_sync import (
    start_signal_reactivation_loop,
)

app.create_task(start_signal_reactivation_loop(app_layer, interval_sec=300))


def main():
    logging.basicConfig(level=logging.INFO)

    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )

    logger.info("🚀 Bot iniciado. Polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
