import logging
from telegram import Bot
from config import TELEGRAM_VIP_CHANNEL_ID

logger = logging.getLogger("notifier")


class Notifier:
    """
    Contrato ÚNICO:
    - constructor requiere bot y chat_id
    - único método público: send(text)
    """

    def __init__(self, bot, chat_id: int):
        if not chat_id:
            raise ValueError("❌ Notifier requiere chat_id válido")
        self.bot = bot
        self.chat_id = chat_id

    async def send(self, text: str):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id, text=text, parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception(f"❌ Error enviando mensaje Telegram: {e}")

    # ------------------------------------------------------------------

    def _format_position_event(self, event: dict) -> str:
        symbol = event.get("symbol", "UNKNOWN")
        side = event.get("side", "?")
        leverage = event.get("leverage", "?")
        roi = event.get("roi", 0.0)
        severity = event.get("severity", "info")
        action = event.get("action", "hold")
        reason = event.get("reason", "")

        icon = {"warning": "⚠️", "critical": "🚨", "force_close": "🛑"}.get(
            severity, "ℹ️"
        )

        action_label = {
            "hold": "MANTENER",
            "reduce": "REDUCIR",
            "close": "CERRAR",
            "reverse": "REVERTIR",
        }.get(action, action.upper())

        return (
            f"{icon} <b>ALERTA DE POSICIÓN</b>\n\n"
            f"📌 <b>Par:</b> {symbol}\n"
            f"📈 <b>Dirección:</b> {side} x{leverage}\n"
            f"📉 <b>ROI:</b> {roi:.2f}%\n\n"
            f"🧠 <b>Acción sugerida:</b> {action_label}\n"
            f"📍 <b>Motivo:</b> {reason}"
        )
