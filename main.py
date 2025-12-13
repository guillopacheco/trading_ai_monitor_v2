# main.py

import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer
from services.telegram_service.command_bot import CommandBot
from services.telegram_service.telegram_reader import start_telegram_reader


# Si tienes monitor de reactivación por loop:
from services.reactivation_engine import start_reactivation_monitor

logger = logging.getLogger("main")


async def post_init(app):
    app.create_task(start_telegram_reader(app_layer))
    app.create_task(start_reactivation_monitor(app_layer))
    logger.info("✅ Background tasks iniciadas correctamente")


application = (
    Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
)

application.run_polling()


def main():
    try:
        logging.basicConfig(level=logging.INFO)

        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .post_init(_post_init)
            .build()
        )

        logger.info("🚀 Bot iniciado. Polling...")
        application.run_polling(close_loop=False)

    except Exception:
        logger.exception("❌ Error crítico en main")


if __name__ == "__main__":
    main()
