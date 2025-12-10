import logging

logger = logging.getLogger("notifier")


import logging

logger = logging.getLogger("notifier")


class Notifier:
    def __init__(self, bot):
        self.bot = bot

    async def send(self, chat_id: int, text: str):
        try:
            await self.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje Telegram: {e}")
