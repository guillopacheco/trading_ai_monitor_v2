# services/telegram_service/notifier.py
import logging
from config import TELEGRAM_CHAT_ID

logger = logging.getLogger("notifier")


class Notifier:
    def __init__(self, bot=None):
        self.bot = bot

    async def send_message(self, text: str, chat_id: int = None):
        if not self.bot:
            logger.warning(f"⚠️ Notifier sin bot. Mensaje omitido: {text[:80]}")
            return
        cid = chat_id or TELEGRAM_CHAT_ID
        await self.bot.send_message(chat_id=cid, text=text)
