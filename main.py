# main.py
import asyncio
import logging

from telegram.ext import Application
from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


async def post_init(app: Application):
    # 1) Construir capa aplicación con BOT real
    app.app_layer = ApplicationLayer(app.bot)

    # 2) Registrar handlers (comandos)
    try:
        from services.telegram_service.command_bot import register_handlers

        register_handlers(app, app.app_layer)
        logger.info("✅ Handlers registrados correctamente")
    except Exception as e:
        logger.exception(f"⚠️ No se pudieron registrar handlers (command_bot): {e}")

    # 3) Reactivation loop
    try:
        from services.signals_service.signal_reactivation_sync import (
            start_signal_reactivation_loop,
        )

        asyncio.create_task(
            start_signal_reactivation_loop(app.app_layer, interval_sec=300)
        )
        logger.info("✅ Loop reactivación iniciado")
    except Exception as e:
        logger.exception(f"❌ No se pudo iniciar loop reactivación: {e}")

    # 4) Open position monitor
    try:
        from services.open_position_engine.position_monitor import (
            start_open_position_monitor,
        )

        asyncio.create_task(start_open_position_monitor(app.app_layer, interval_sec=60))
        logger.info("✅ Monitor posiciones abiertas iniciado")
    except Exception as e:
        logger.exception(f"❌ No se pudo iniciar monitor de posiciones abiertas: {e}")

    # 5) Telethon reader
    try:
        from services.telegram_service.telegram_reader import start_telegram_reader

        asyncio.create_task(start_telegram_reader(app.app_layer))
        logger.info("✅ Telegram reader (Telethon) iniciado")
    except Exception as e:
        logger.exception(f"❌ No se pudo iniciar Telegram reader: {e}")

    logger.info("✅ Background tasks iniciadas correctamente")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN/BOT_TOKEN en .env")

    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )

    logger.info("🚀 Bot iniciado. Polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
