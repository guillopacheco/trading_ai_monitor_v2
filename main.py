# main.py
import asyncio
import logging

from telegram.ext import ApplicationBuilder

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer

logger = logging.getLogger("main")


async def post_init(app):
    # ✅ App layer estable (siempre recibe bot)
    app.app_layer = ApplicationLayer(bot=app.bot)

    # ✅ Registrar comandos (si existe)
    try:
        from services.telegram_service.command_bot import register_handlers

        register_handlers(app, app.app_layer)
        logger.info("✅ Handlers registrados correctamente")
    except Exception as e:
        logger.exception(f"⚠️ No se pudieron registrar handlers (command_bot): {e}")

    # ✅ Background tasks (SIN Application.create_task → sin warning PTB)
    try:
        from services.signals_service.signal_reactivation_sync import (
            start_signal_reactivation_loop,
        )

        asyncio.create_task(
            start_signal_reactivation_loop(app.app_layer, interval_sec=300)
        )
        logger.info("✅ Loop reactivación iniciado")
    except Exception as e:
        logger.exception(f"❌ No se pudo iniciar loop de reactivación: {e}")

    try:
        from services.open_position_engine.position_monitor import (
            start_open_position_monitor,
        )

        asyncio.create_task(
            start_open_position_monitor(app.app_layer, interval_sec=120)
        )
        logger.info("✅ Monitor posiciones abiertas iniciado")
    except Exception as e:
        logger.exception(f"❌ No se pudo iniciar monitor de posiciones abiertas: {e}")

    try:
        from services.telegram_service.telegram_reader import start_telegram_reader

        asyncio.create_task(start_telegram_reader(app.app_layer))
        logger.info("✅ Telegram reader (Telethon) iniciado")
    except Exception as e:
        logger.exception(f"❌ No se pudo iniciar Telegram reader: {e}")

    logger.info("✅ Background tasks iniciadas correctamente")


def main():
    logging.basicConfig(level=logging.INFO)

    application = (
        ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )

    logger.info("🚀 Bot iniciado. Polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
