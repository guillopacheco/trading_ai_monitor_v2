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
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    notifier = Notifier(application.bot)
    app_layer = ApplicationLayer(notifier)

    command_bot = CommandBot(app_layer)
    command_bot.run()

    # Mantener bot vivo
    await bot_app.updater.wait_for_stop()

    logger.info("🛑 Servicios cerrados.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}", exc_info=True)
