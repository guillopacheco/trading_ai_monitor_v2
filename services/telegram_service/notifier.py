import logging
from telegram import Bot

logger = logging.getLogger("notifier")


class Notifier:
    """
    Capa unificada para enviar mensajes a Telegram.
    Se configura dinámicamente desde ApplicationLayer.set_bot().
    """

    def __init__(self):
        self.bot: Bot | None = None
        self.chat_id: int | None = None

    # ---------------------------------------------------------
    # CONFIGURACIÓN
    # ---------------------------------------------------------
    def configure(self, bot: Bot, chat_id: int):
        """
        Se llama desde ApplicationLayer.set_bot() para inyectar
        el bot real y el chat destino.
        """
        self.bot = bot
        self.chat_id = chat_id
        logger.info("📨 Notifier configurado correctamente con bot y chat_id.")

    # ---------------------------------------------------------
    # MÉTODOS SEGUROS
    # ---------------------------------------------------------
    async def safe_send(self, text: str):
        """
        Envía mensajes de forma segura sin detener la app.
        """
        if not self.bot or not self.chat_id:
            logger.error("❌ Notifier no configurado con bot/chat_id")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje Telegram: {e}", exc_info=True)

    async def send_message(self, text: str):
        """Alias por compatibilidad."""
        await self.safe_send(text)
