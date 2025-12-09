# services/telegram_service/notifier.py

import logging
from telegram import Bot

logger = logging.getLogger("notifier")


class Notifier:
    """
    Wrapper centralizado para enviar mensajes a Telegram desde cualquier servicio.
    """

    def __init__(self, bot: Bot = None, chat_id: str = None):
        """
        Si no se pasa bot/chat_id, se obtendrán desde ApplicationLayer.
        """
        self.bot = bot
        self.chat_id = chat_id

    # ============================================================
    # Métodos de inicialización (útiles cuando se inyecta el bot)
    # ============================================================
    def configure(self, bot: Bot, chat_id: str):
        """Permite configurar el bot después de instanciar la clase."""
        self.bot = bot
        self.chat_id = chat_id

    # ============================================================
    # MÉTODO PRINCIPAL - send_message (AGREGAR ESTE)
    # ============================================================
    async def send_message(self, text: str):
        """
        Envía un mensaje básico (alias de send para compatibilidad).
        """
        await self.send(text)

    async def send(self, text: str):
        """
        Envía un mensaje básico.
        """
        if not self.bot or not self.chat_id:
            logger.error("❌ Notifier no configurado con bot/chat_id")
            return

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            logger.exception(f"❌ Error enviando mensaje por Telegram: {e}")

    async def notify_analysis(self, formatted_text: str):
        """
        Enviar análisis técnico formateado.
        """
        await self.send(formatted_text)

    async def notify_reactivation(self, text: str):
        """
        Enviar notificación de reactivación.
        """
        await self.send(text)

    async def notify_position_event(self, text: str):
        """
        Notificación para eventos de posiciones (cierres, reversión, riesgo, etc).
        """
        await self.send(text)

    async def notify_error(self, text: str):
        """
        Notificación de errores severos.
        """
        await self.send(f"⚠️ ERROR: {text}")
