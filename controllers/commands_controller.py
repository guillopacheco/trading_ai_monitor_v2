"""
commands_controller.py (versión integrada A+)
--------------------------------------------
Controlador de comandos del bot.

✔ Totalmente conectado al Motor Técnico A+
✔ Sin dependencias circulares
✔ Usa import diferido para Telegram
"""

from __future__ import annotations
import logging

logger = logging.getLogger("commands_controller")


# ============================================================
# 📡 Bridge seguro hacia telegram_service
# ============================================================

def safe_send(msg: str) -> None:
    """Envía mensajes sin generar ciclos."""
    try:
        from services.telegram_service import send_message
        send_message(msg)
    except Exception as e:
        logger.error(f"❌ Error en safe_send: {e}")


# ============================================================
# 🧠 Ejecutar análisis manual usando el Motor Técnico A+
# ============================================================

def run_manual_analysis(symbol: str) -> None:
    """Ejecuta el análisis técnico completo del Motor A+."""
    try:
        from core.signal_engine import analyze_symbol  # import diferido
    except Exception as e:
        safe_send(f"❌ Error importando el motor técnico: {e}")
        return

    try:
        result = analyze_symbol(symbol)
    except Exception as e:
        safe_send(f"❌ Error ejecutando análisis técnico: {e}")
        return

    # Enviar directamente el texto generado por el motor
    safe_send(result.get("message", "⚠️ Hubo un error generando el análisis."))


# ============================================================
# 🧠 Ejecutar comando
# ============================================================

def execute_command(text: str) -> None:
    """Procesa TODOS los comandos."""
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
        safe_send(
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
        safe_send(
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
        safe_send("🏓 Pong! El bot está activo.")
        return

    # ---------------------------------------------------------
    # /analizar
    # ---------------------------------------------------------
    if cmd == "/analizar":
        if not args:
            safe_send("⚠️ Usa: `/analizar BTCUSDT`")
            return

        symbol = args[0].upper()
        safe_send(f"🔍 *Analizando {symbol}...* (Motor Técnico A+)")
        run_manual_analysis(symbol)
        return

    # ---------------------------------------------------------
    # No reconocido
    # ---------------------------------------------------------
    safe_send(
        f"❓ Comando no reconocido: `{cmd}`\n"
        "Usa `/help` para más información."
    )
