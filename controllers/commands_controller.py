from services.telegram_sender import send
from core.signal_engine import analyze_manual_symbol
import logging

logger = logging.getLogger("commands_controller")


async def execute_command(cmd, args):
    """Procesa comandos del bot."""
    if cmd == "/analizar":
        if not args:
            await send("❌ Debes indicar un par. Ej: /analizar BTCUSDT")
            return

        symbol = args[0].upper()
        result = await analyze_manual_symbol(symbol)
        await send(result)
