"""
controllers/commands_controller.py
----------------------------------
Controlador de comandos del bot.

Por ahora:
    /help
    /analizar {PAR}
"""

import logging
from typing import List

from services.telegram_service import safe_send
from core.signal_engine import analyze_manual_symbol

logger = logging.getLogger("commands_controller")


async def execute_command(command: str, args: List[str]) -> None:
    cmd = (command or "").lower()

    if cmd in ("/start", "/help"):
        await _cmd_help()
    elif cmd == "/analizar":
        await _cmd_analizar(args)
    else:
        await safe_send(f"❓ Comando no reconocido: {cmd}")


async def _cmd_help() -> None:
    text = (
        "🤖 *Trading AI Monitor*\n\n"
        "Comandos disponibles:\n"
        "• `/help` – Muestra esta ayuda\n"
        "• `/analizar PAR` – Analiza técnicamente un par, e.g. `/analizar CUDISUSDT`\n"
    )
    await safe_send(text)


async def _cmd_analizar(args: List[str]) -> None:
    if not args:
        await safe_send("⚠️ Uso correcto: `/analizar PAR`, por ejemplo: `/analizar CUDISUSDT`")
        return

    symbol = args[0].upper()
    logger.info(f"🔍 /analizar solicitado para {symbol}")

    try:
        analysis = analyze_manual_symbol(symbol)
    except Exception as e:
        logger.error(f"❌ Error en analyze_manual_symbol: {e}")
        await safe_send(f"❌ Error analizando {symbol}: {e}")
        return

    msg = analysis.get("message") or f"📊 Análisis de {symbol} completado."
    await safe_send(msg)
