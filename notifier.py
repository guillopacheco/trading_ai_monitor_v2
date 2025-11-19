"""
notifier.py — módulo unificado de notificaciones Telegram
---------------------------------------------------------
- Envío de mensajes al usuario propietario del bot
- Helpers para alertas de operaciones
---------------------------------------------------------
"""

import logging
import asyncio
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID

logger = logging.getLogger("notifier")


# ============================================================
# 📨 Envío genérico de mensajes
# ============================================================

async def send_message(text: str):
    """
    Envía un mensaje al usuario principal vía Bot API.
    Uso:
        await send_message("Hola")
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
        logger.error("❌ TELEGRAM_BOT_TOKEN o TELEGRAM_USER_ID no configurados.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_USER_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    def _post():
        try:
            r = requests.post(url, data=payload, timeout=10)
            if not r.ok:
                logger.error(f"❌ Error enviando mensaje Telegram: {r.text}")
        except Exception as e:
            logger.error(f"❌ Excepción en send_message: {e}")

    # Ejecutar el POST en un thread para no bloquear el loop
    await asyncio.to_thread(_post)


# ============================================================
# 🚨 Helper específico para alertas de operaciones
# ============================================================

def build_operation_alert_message(
    symbol: str,
    direction: str,
    roi: float,
    pnl: float,
    loss_level: int | None,
    volatility: str,
    suggestion: str,
) -> str:
    emoji_dir = "🟢" if direction.lower() == "long" else "🔴"
    return (
        f"🚨 *Alerta de operación: {symbol}*\n"
        f"{emoji_dir} Dirección: *{direction.upper()}*\n"
        f"💵 ROI: `{roi:.2f}%`\n"
        f"💰 PnL: `{pnl}`\n"
        f"📉 Nivel de pérdida: {loss_level}%\n"
        f"🧭 Tendencia mayor: {volatility}\n"
        f"🧠 *Recomendación:* {suggestion}"
    )


async def notify_operation_alert_async(
    symbol: str,
    direction: str,
    roi: float,
    pnl: float,
    loss_level: int | None,
    volatility: str,
    suggestion: str,
):
    msg = build_operation_alert_message(
        symbol=symbol,
        direction=direction,
        roi=roi,
        pnl=pnl,
        loss_level=loss_level,
        volatility=volatility,
        suggestion=suggestion,
    )
    await send_message(msg)


def notify_operation_alert(
    symbol: str,
    direction: str,
    roi: float,
    pnl: float,
    loss_level: int | None,
    volatility: str,
    suggestion: str,
):
    """
    Versión SINCRÓNICA para ser llamada desde código no-async.
    Internamente lanza una tarea async.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No hay loop -> crear uno nuevo solo para este envío
        asyncio.run(
            notify_operation_alert_async(
                symbol, direction, roi, pnl, loss_level, volatility, suggestion
            )
        )
        return

    # Si ya hay loop corriendo:
    if loop.is_running():
        asyncio.create_task(
            notify_operation_alert_async(
                symbol, direction, roi, pnl, loss_level, volatility, suggestion
            )
        )
    else:
        loop.run_until_complete(
            notify_operation_alert_async(
                symbol, direction, roi, pnl, loss_level, volatility, suggestion
            )
        )
