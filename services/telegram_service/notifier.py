import logging
from telegram import Bot
from config import TELEGRAM_CHAT_ID

logger = logging.getLogger("notifier")


class Notifier:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_position_event(self, event: dict):
        """
        Envía una alerta de posición abierta a Telegram.
        No decide lógica. Solo presenta información.
        """

        try:
            message = self._format_position_event(event)

            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML"
            )

            logger.info(
                f"📤 Alerta enviada: {event.get('symbol')} "
                f"action={event.get('action')} severity={event.get('severity')}"
            )

        except Exception as e:
            logger.exception(f"❌ Error enviando alerta Telegram: {e}")

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
