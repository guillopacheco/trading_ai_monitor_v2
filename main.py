import asyncio
import logging
from logger_config import configure_logging
from database import init_db
from application_layer import ApplicationLayer
from services.telegram_service.command_bot import start_command_bot
from services.telegram_service.telegram_reader import start_telegram_reader
from services.signals_service.signal_reactivation_sync import start_reactivation_monitor

logger = logging.getLogger("MAIN")


async def main():
    configure_logging()
    logger.info("🚀 Trading AI Monitor iniciando...")

    # ------------------------------------------------------------------
    # DB
    # ------------------------------------------------------------------
    init_db()
    logger.info("✅ Base de datos inicializada correctamente.")

    # ------------------------------------------------------------------
    # Application Layer
    # ------------------------------------------------------------------
    app_layer = ApplicationLayer()

    # ------------------------------------------------------------------
    # Start services async
    # ------------------------------------------------------------------
    logger.info("📡 Iniciando servicios…")

    bot_app = await start_command_bot(app_layer)

    await asyncio.gather(
        start_telegram_reader(app_layer),
        start_reactivation_monitor(app_layer),
    )

    # Mantener bot vivo
    await bot_app.updater.wait_for_stop()

    logger.info("🛑 Servicios cerrados.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}", exc_info=True)
