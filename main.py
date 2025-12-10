import asyncio
import logging

from telegram.ext import Application
from config import TELEGRAM_BOT_TOKEN
from services.telegram_service.notifier import Notifier
from application_layer import ApplicationLayer
from services.telegram_service.command_bot import CommandBot

logger = logging.getLogger("MAIN")


async def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    notifier = Notifier(application.bot)
    app_layer = ApplicationLayer(notifier)

    command_bot = CommandBot(app_layer, application)
    command_bot.run()


if __name__ == "__main__":
    asyncio.run(main())
