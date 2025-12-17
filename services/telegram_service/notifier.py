import logging
from telegram import Bot
from config import TELEGRAM_VIP_CHANNEL_ID

logger = logging.getLogger("notifier")


class Notifier:
    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id

    async def send_message(self, text: str):
        if not self.chat_id:
            raise RuntimeError("chat_id no configurado en Notifier")

        await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="HTML")

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
