"""
commands_controller.py (versión async corregida)
-----------------------------------------------
Controlador de comandos del bot (async-safe).

✔ safe_send() YA no genera advertencias
✔ execute_command() ahora es async
✔ send_message() se await-ea correctamente
"""

from __future__ import annotations
import logging
import asyncio

logger = logging.getLogger("commands_controller")


# ============================================================
# 📡 Bridge seguro hacia telegram_service (async)
# ============================================================

async def safe_send(msg: str):
    """Envía mensajes al bot de forma segura, evitando ciclos y warnings."""
    try:
        from services.telegram_service import send_message  # async
        await send_message(msg)
    except Exception as e:
        logger.error(f"❌ Error en safe_send: {e}")


# ============================================================
# 🧠 Ejecutar análisis manual usando el Motor Técnico A+
# ============================================================

async def run_manual_analysis(symbol: str):
    """Ejecuta el análisis técnico completo del Motor A+."""
    try:
        from core.signal_engine import analyze_symbol  # async-safe
    except Exception as e:
        await safe_send(f"❌ Error importando el motor técnico: {e}")
        return

    try:
        result = analyze_symbol(symbol)
    except Exception as e:
        await safe_send(f"❌ Error ejecutando análisis técnico: {e}")
        return

    await safe_send(result.get("message", "⚠️ Hubo un error generando el análisis."))


# ============================================================
# 🧠 Ejecutar comando (ASYNC)
# ============================================================

async def execute_command(text: str):
    """Procesa TODOS los comandos del bot (async)."""
    if not text:
        return

    parts = text.strip().split()
    cmd = parts[0].lower()
    args = parts[1:]

    logger.info(f"📥 Comando recibido: {cmd} {args}")

    # ---------------------------------------------------------
    # /start
    # ---------------------------------------------------------
    if cmd == "/start":
        await safe_send(
            "👋 *Bienvenido a Trading AI Monitor v2*\n\n"
            "Comandos:\n"
            "• `/help`\n"
            "• `/analizar BTCUSDT`\n"
            "• `/ping`\n"
        )
        return

    # ---------------------------------------------------------
    # /help
    # ---------------------------------------------------------
    if cmd == "/help":
        await safe_send(
            "📚 *Ayuda — Comandos*\n\n"
            "• `/start` → bienvenida\n"
            "• `/help` → esta ayuda\n"
            "• `/analizar PAR` → análisis técnico instantáneo\n"
            "• `/ping` → estado del bot\n"
        )
        return

    # ---------------------------------------------------------
    # /ping
    # ---------------------------------------------------------
    if cmd == "/ping":
        await safe_send("🏓 Pong! El bot está activo.")
        return

    # ---------------------------------------------------------
    # /analizar
    # ---------------------------------------------------------
    if cmd == "/analizar":
        if not args:
            await safe_send("⚠️ Usa: `/analizar BTCUSDT`")
            return

        symbol = args[0].upper()
        await safe_send(f"🔍 *Analizando {symbol}...* (Motor Técnico A+)")
        await run_manual_analysis(symbol)
        return

    # ---------------------------------------------------------
    # No reconocido
    # ---------------------------------------------------------
    await safe_send(
        f"❓ Comando no reconocido: `{cmd}`\n"
        "Usa `/help` para más información."
    )
