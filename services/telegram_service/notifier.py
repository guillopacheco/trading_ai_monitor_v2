import logging
from telegram import Bot
from config import TELEGRAM_USER_ID

logger = logging.getLogger("notifier")


class Notifier:
    """
    Enviar mensajes a Telegram usando el bot ya inicializado en main.py
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.chat_id = TELEGRAM_USER_ID

    async def safe_send(self, text: str):
        """Envía mensaje a Telegram, capturando errores sin romper el sistema."""
        if not self.bot:
            logger.error("❌ Notifier no configurado con bot.")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
            logger.info(f"📨 Notificado: {text[:60]}")
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje Telegram: {e}")

    async def send_message(self, text: str):
        """Alias por compatibilidad con módulos antiguos."""
        await self.safe_send(text)
