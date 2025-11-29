"""
controllers/commands_controller.py
----------------------------------
Controlador de comandos del bot.

No importa directamente telegram_service al inicio para evitar ciclos.
Usa un bridge seguro (safe_send) que hace import diferido cuando se necesita.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("commands_controller")


# ============================================================
# 📡 Bridge seguro hacia telegram_service (evita ciclos)
# ============================================================

def safe_send(msg: str) -> None:
    """
    Envía un mensaje al usuario usando telegram_service.send_message,
    pero hace el import de forma diferida para evitar import circular.
    """
    try:
        from services.telegram_service import send_message  # type: ignore
        send_message(msg)
    except Exception as e:
        # No romper la app por un fallo de notificación
        logger.error(f"❌ Error en safe_send (commands_controller): {e}")


# ============================================================
# 🧠 Ejecutor de comandos
# ============================================================

def execute_command(text: str) -> None:
    """
    Punto de entrada único para TODOS los comandos tipo /comando.

    Se asume que `text` es el mensaje completo recibido, por ejemplo:
        "/start"
        "/help"
        "/ping"
        "/analizar BTCUSDT"
    """

    if not text:
        return

    parts = text.strip().split()
    cmd = parts[0].lower()
    args = parts[1:]

    logger.info(f"📥 Comando recibido: {cmd} {args}")

    # ------------------------------
    # /start
    # ------------------------------
    if cmd == "/start":
        safe_send(
            "👋 *Bienvenido a Trading AI Monitor v2*\n\n"
            "Envíame comandos como:\n"
            "• `/help` → ver ayuda\n"
            "• `/ping` → comprobar estado del bot\n"
            "• `/analizar BTCUSDT` → (próximamente) analizar un par concreto\n"
        )
        return

    # ------------------------------
    # /help
    # ------------------------------
    if cmd == "/help":
        safe_send(
            "📚 *Ayuda — Comandos disponibles*\n\n"
            "• `/start` → mensaje de bienvenida\n"
            "• `/help` → esta ayuda\n"
            "• `/ping` → comprobar estado\n"
            "• `/analizar {par}` → (en desarrollo) análisis manual\n"
        )
        return

    # ------------------------------
    # /ping
    # ------------------------------
    if cmd == "/ping":
        safe_send("🏓 Pong! El bot está en línea y funcionando.")
        return

    # ------------------------------
    # /analizar {par}  (placeholder)
    # ------------------------------
    if cmd == "/analizar":
        if not args:
            safe_send("⚠️ Usa: `/analizar BTCUSDT`")
            return

        par = args[0].upper()
        # Aquí en futuras iteraciones conectaremos con signal_engine.analyze_open_position
        safe_send(
            f"🔍 Análisis manual solicitado para *{par}*.\n"
            "Esta función está en proceso de integración con el Motor Técnico A+."
        )
        return

    # ------------------------------
    # Comando no reconocido
    # ------------------------------
    safe_send(
        f"❓ Comando no reconocido: `{cmd}`\n"
        "Usa `/help` para ver la lista de comandos disponibles."
    )
