import logging

from controllers.signal_listener import on_new_signal
from controllers.commands_controller import execute_command
from utils.helpers import is_command, extract_command
from services.telegram_service import safe_send

logger = logging.getLogger("telegram_router")


async def route_incoming_message(text: str):
    """
    Router oficial de mensajes entrantes desde Telegram.
    Distingue entre comandos y señales VIP.
    """

    if not text or not isinstance(text, str):
        return

    # ---------------------------------------------------
    # 🔍 1) Detectar comando (/analizar, /help, /revisar…)
    # ---------------------------------------------------
    if is_command(text):
        cmd, args = extract_command(text)

        logger.info(f"📥 Comando detectado: {cmd} {args}")

        try:
            # 🔥🔥 AGREGADO: ahora SÍ se hace await
            await execute_command(cmd, args)

        except Exception as e:
            logger.error(f"❌ Error ejecutando comando {cmd}: {e}", exc_info=True)
            await safe_send(f"❌ Error ejecutando comando {cmd}.\n{e}")

        return

    # ---------------------------------------------------
    # 🔍 2) Señal normal del canal VIP
    # ---------------------------------------------------
    logger.info(f"📩 Señal recibida desde router: {text[:60]}...")

    try:
        # 🔥🔥 AGREGADO: ahora SÍ se hace await
        await on_new_signal(text)

    except Exception as e:
        logger.error(f"❌ Error procesando señal: {e}", exc_info=True)
        await safe_send(f"❌ Error procesando señal.\n{e}")
