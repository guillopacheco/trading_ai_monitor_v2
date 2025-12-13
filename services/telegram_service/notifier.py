import logging
from telegram import Bot
from config import TELEGRAM_USER_ID

logger = logging.getLogger("notifier")


class Notifier:
    def __init__(self, bot):
        self.bot = bot

    async def send_message(self, chat_id: int, text: str, **kwargs):
        try:
            await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception as e:
            logger.exception(f"❌ Error enviando mensaje: {e}")

    async def safe_send(self, chat_id: int, text: str, **kwargs):
        await self.send_message(chat_id, text, **kwargs)
