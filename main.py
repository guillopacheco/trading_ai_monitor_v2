import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from services.telegram_service.notifier import Notifier
from services.telegram_service.command_bot import CommandBot
from application_layer import ApplicationLayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAIN")


def main():
    # 1️⃣ Crear Application de Telegram (maneja su propio event loop)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 2️⃣ Crear notifier con el bot
    notifier = Notifier(application.bot)

    # 3️⃣ Crear Application Layer (core)
    app_layer = ApplicationLayer(notifier)

    # 4️⃣ Crear CommandBot
    command_bot = CommandBot(app_layer, application)

    # 5️⃣ Arrancar polling (bloqueante, correcto)
    command_bot.run()


if __name__ == "__main__":
    main()
