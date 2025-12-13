# main.py
import logging

from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from application_layer import ApplicationLayer
from services.telegram_service.command_bot import CommandBot

logger = logging.getLogger("MAIN")


async def _post_init(application: Application) -> None:
    """
    Se ejecuta cuando PTB ya tiene loop corriendo e inicializa cosas async-safe.
    Aquí registramos handlers y lanzamos tareas de background sin romper el event loop.
    """
    logger.info("⚙️ post_init: creando ApplicationLayer y registrando CommandBot...")

    # 1) App layer (inyectamos el bot real de PTB)
    app_layer = ApplicationLayer(application.bot)

    # 2) Command bot (handlers)
    cmd = CommandBot(application=application, app_layer=app_layer)
    cmd.register_handlers()

    # 3) Guardar referencias por si las quieres consultar luego
    application.bot_data["app_layer"] = app_layer
    application.bot_data["command_bot"] = cmd

    # 4) Background tasks (si existen en tu proyecto)
    #    IMPORTANTE: se lanzan con application.create_task() para evitar "event loop already running"
    try:
        from services.telegram_service.telegram_reader import start_telegram_reader

        application.create_task(start_telegram_reader(app_layer))
        logger.info("📡 telegram_reader: task iniciada")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo iniciar telegram_reader: {e}")

    try:
        from services.signals_service.signal_reactivation_sync import (
            start_reactivation_monitor,
        )

        application.create_task(start_reactivation_monitor(app_layer))
        logger.info("♻️ reactivation_monitor: task iniciada")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo iniciar reactivation_monitor: {e}")


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.info("🚀 Trading AI Monitor iniciando...")

    application = (
        Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(_post_init).build()
    )

    # PTB maneja su propio loop aquí (NO asyncio.run)
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("❌ Error crítico en main")
        raise
