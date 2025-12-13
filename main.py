# main.py

import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer
from services.telegram_service.command_bot import CommandBot

# Si tienes monitor de reactivación por loop:
from services.signals_service.signal_reactivation_sync import start_reactivation_monitor

logger = logging.getLogger("main")


async def _post_init(application: Application):
    """
    Se ejecuta una vez el bot ya inicializó.
    Aquí construimos ApplicationLayer con application.bot (PTB bot real).
    """
    app_layer = ApplicationLayer(application.bot)
    application.bot_data["app_layer"] = app_layer

    # Registrar handlers
    CommandBot(application, app_layer)

    # Iniciar background monitor de reactivación (si existe)
    try:
        application.create_task(start_reactivation_monitor(app_layer))
        logger.info("✅ Monitor reactivación iniciado.")
    except Exception as e:
        logger.warning(f"⚠️ No se inició monitor de reactivación: {e}")


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
