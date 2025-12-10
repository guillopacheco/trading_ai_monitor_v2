import logging

logger = logging.getLogger("notifier")


class Notifier:
    def __init__(self):
        self.bot = None
        self.chat_id = None

    def configure(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    async def send_message(self, text: str):
        if not self.bot or not self.chat_id:
            logger.error("❌ Notifier no configurado con bot/chat_id")
            return
        await self.bot.send_message(chat_id=self.chat_id, text=text)
