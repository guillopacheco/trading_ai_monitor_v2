# main.py
import asyncio
import logging

from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer

logger = logging.getLogger("main")


async def post_init(app: Application):
    """
    Se ejecuta dentro del loop asyncio de python-telegram-bot.
    Aquí inicializamos la capa de aplicación y lanzamos tareas de fondo
    sin depender de variables globales tipo `app`.
    """
    # 1) Construir ApplicationLayer con el bot real
    app.app_layer = ApplicationLayer(bot=app.bot)

    # 2) Registrar comandos/handlers (compat: register_handlers o setup_handlers)
    try:
        from services.telegram_service.command_bot import register_handlers

        register_handlers(app, app.app_layer)
        logger.info("✅ Handlers registrados con register_handlers()")
    except Exception:
        try:
            from services.telegram_service.command_bot import setup_handlers

            setup_handlers(app, app.app_layer)
            logger.info("✅ Handlers registrados con setup_handlers()")
        except Exception as e:
            logger.exception("⚠️ No se pudieron registrar handlers (command_bot): %s", e)

    # 3) Tareas de fondo (reactivación + operaciones abiertas + telethon)
    try:
        from services.signals_service.signal_reactivation_sync import (
            start_signal_reactivation_loop,
        )

        app.create_task(start_signal_reactivation_loop(app.app_layer, interval_sec=300))
        logger.info("✅ Loop reactivación iniciado")
    except Exception as e:
        logger.exception("❌ No se pudo iniciar loop reactivación: %s", e)

    try:
        # Si tu monitor se llama distinto, ajusta el import al nombre real
        from services.open_position_engine.position_monitor import (
            start_open_position_monitor,
        )

        app.create_task(start_open_position_monitor(app.app_layer, interval_sec=60))
        logger.info("✅ Monitor posiciones abiertas iniciado")
    except Exception as e:
        logger.exception("❌ No se pudo iniciar monitor de posiciones abiertas: %s", e)

    try:
        from services.telegram_service.telegram_reader import start_telegram_reader

        app.create_task(start_telegram_reader(app.app_layer))
        logger.info("✅ Telegram reader (Telethon) iniciado")
    except Exception as e:
        logger.exception("❌ No se pudo iniciar telegram_reader: %s", e)

    logger.info("✅ Background tasks iniciadas correctamente")


def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("🚀 Bot iniciado. Polling...")

    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    )
    application.run_polling()


if __name__ == "__main__":
    main()
