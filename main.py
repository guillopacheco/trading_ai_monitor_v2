import asyncio
import logging

from telegram.ext import Application
from config import TELEGRAM_BOT_TOKEN

from application_layer import ApplicationLayer
from services.telegram_service.command_bot import CommandBot
from services.telegram_service.telegram_reader import start_telegram_reader


logger = logging.getLogger("MAIN")


async def main():
    logger.info("🚀 Trading AI Monitor iniciando...")

    # ---------------------------------------------------------
    # 1) Crear ApplicationLayer (núcleo de servicios)
    # ---------------------------------------------------------
    app_layer = ApplicationLayer()

    # ---------------------------------------------------------
    # 2) Crear instancia del bot Telegram
    # ---------------------------------------------------------
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Conectar el notifier dentro del ApplicationLayer
    app_layer.set_bot(bot_app.bot)

    # ---------------------------------------------------------
    # 3) Cargar CommandBot (registrar comandos)
    # ---------------------------------------------------------
    command_bot = CommandBot(app_layer, bot_app)

    # ---------------------------------------------------------
    # 4) Iniciar proceso paralelo de lectura del canal VIP
    # ---------------------------------------------------------
    asyncio.create_task(start_telegram_reader(app_layer))

    # ---------------------------------------------------------
    # 5) Iniciar reactivate_sync en background
    # ---------------------------------------------------------
    logger.info("🔁 Activando motor de reactivación…")
    asyncio.create_task(app_layer.start_reactivation_monitor())

    # ---------------------------------------------------------
    # 6) Iniciar monitor de posiciones (pero no empieza aún)
    #     Solo se activará cuando el usuario use /reanudar
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # 7) Iniciar bot (bloqueante)
    # ---------------------------------------------------------
    logger.info("🤖 Iniciando bot Telegram…")
    await bot_app.run_polling(close_loop=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}", exc_info=True)
