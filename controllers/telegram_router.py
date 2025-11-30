import logging
from utils.helpers import is_command, extract_command
from controllers.commands_controller import execute_command
from controllers.signal_listener import on_new_signal

logger = logging.getLogger("telegram_router")


async def route_incoming_message(raw_text: str):
    """Router central para comandos y señales VIP."""

    if is_command(raw_text):
        cmd, args = extract_command(raw_text)
        logger.info(f"📥 Comando recibido: {cmd} {args}")
        await execute_command(cmd, args)
        return

    # Señal de VIP
    await on_new_signal(raw_text)
