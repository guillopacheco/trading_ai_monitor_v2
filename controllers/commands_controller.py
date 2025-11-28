"""
commands_controller.py
-----------------------
Controlador oficial de comandos del bot.

Este módulo NO se comunica directamente con Telegram ni con Bybit.
Solo recibe "command" y "params" desde telegram_service y ejecuta
la acción correspondiente.

Flujo:
    telegram_service → commands_controller → services/core

Comandos incluidos:
    /start
    /help
    /analizar {par}
    /revisar
    /detener
    /historial
    /signal {texto crudo}
    /ping
"""

import logging
from typing import Optional

from services.telegram_service import send_message
from services import db_service
from core.signal_engine import analyze_signal
from controllers.signal_controller import process_new_signal

logger = logging.getLogger("commands_controller")

# Estado interno del sistema (se irá moviendo a un TaskManager)
SYSTEM_STATE = {
    "monitor_active": False,
    "monitor_task": None,
}


# ============================================================
# 🔵 FUNCIÓN PRINCIPAL DEL CONTROLADOR
# ============================================================
async def handle_command(command: str, params: str):
    logger.info(f"⚙ Procesando comando: {command} {params}")

    try:
        if command == "/start":
            await _cmd_start()

        elif command == "/help":
            await _cmd_help()

        elif command == "/ping":
            await send_message("🏓 Pong!")

        elif command == "/analizar":
            await _cmd_analizar(params)

        elif command == "/revisar":
            await _cmd_revisar()

        elif command == "/detener":
            await _cmd_detener()

        elif command == "/historial":
            await _cmd_historial()

        elif command == "/signal":
            await _cmd_signal_manual(params)

        else:
            await send_message(f"❓ Comando desconocido: {command}")

    except Exception as e:
        logger.error(f"❌ Error ejecutando comando {command}: {e}")
        await send_message("❌ Error ejecutando el comando.")


# ============================================================
# 🔵 COMANDO: /start
# ============================================================
async def _cmd_start():
    msg = (
        "🤖 **Trading AI Monitor iniciado**\n\n"
        "Comandos disponibles:\n"
        " /analizar BTCUSDT — analiza un par\n"
        " /signal ... — procesa una señal manual\n"
        " /revisar — inicia monitoreo de posiciones\n"
        " /detener — detiene monitoreo\n"
        " /historial — muestra últimos análisis\n"
        " /help — ver ayuda completa\n"
    )
    await send_message(msg)


# ============================================================
# 🔵 COMANDO: /help
# ============================================================
async def _cmd_help():
    msg = (
        "📘 **Ayuda del sistema**\n\n"
        "/start — iniciar bot\n"
        "/analizar BTCUSDT — análisis técnico completo\n"
        "/signal texto_de_señal — procesar señal manual\n"
        "/revisar — activar monitor de posiciones\n"
        "/detener — detener monitor\n"
        "/historial — ver últimos 50 logs\n"
        "/ping — test de respuesta\n"
    )
    await send_message(msg)


# ============================================================
# 🔵 COMANDO: /analizar PAR
# ============================================================
async def _cmd_analizar(params: str):
    if not params:
        return await send_message("⚠️ Debes indicar un par. Ejemplo:\n/analizar BTCUSDT")

    symbol = params.strip().upper()
    direction = "long"  # análisis neutral, pero requerido por motor

    await send_message(f"🔍 Analizando {symbol}…")

    analysis = await analyze_signal(symbol, direction)

    msg = (
        f"📊 **Análisis técnico de {symbol}**\n\n"
        f"Match Ratio: {analysis['match_ratio']}%\n"
        f"Grado: {analysis['grade']}\n"
        f"Decisión: {analysis['decision']}\n\n"
        f"Detalles:\n{analysis['details']}"
    )
    await send_message(msg)


# ============================================================
# 🔵 COMANDO: /revisar
# ============================================================
async def _cmd_revisar():
    if SYSTEM_STATE["monitor_active"]:
        return await send_message("⚠️ El monitor ya está activo.")

    SYSTEM_STATE["monitor_active"] = True
    await send_message("📡 Monitor de posiciones activado.")

    # Aquí se conectará al positions_controller futuramente.
    # Por ahora solo placeholder.
    logger.info("Monitor ON (placeholder).")


# ============================================================
# 🔵 COMANDO: /detener
# ============================================================
async def _cmd_detener():
    if not SYSTEM_STATE["monitor_active"]:
        return await send_message("⚠️ El monitor ya está detenido.")

    SYSTEM_STATE["monitor_active"] = False

    await send_message("🛑 Monitor de posiciones detenido.")


# ============================================================
# 🔵 COMANDO: /historial
# ============================================================
async def _cmd_historial():
    logs = db_service.get_logs(limit=20)

    if not logs:
        return await send_message("📭 No hay registros.")

    text = "🗄 **Últimos análisis técnicos:**\n\n"
    for log in logs:
        text += (
            f"• {log['timestamp']} — #{log['signal_id']} — "
            f"{log['recommendation']} ({log['match_ratio']}%)\n"
        )

    await send_message(text)


# ============================================================
# 🔵 COMANDO: /signal (ingresar una señal manual)
# ============================================================
async def _cmd_signal_manual(params: str):
    """
    Permite pegar una señal textual directamente desde Telegram.
    """

    if not params or len(params) < 5:
        return await send_message("⚠️ Debes incluir una señal.\nEj: `/signal LONG BTCUSDT 0.1234`")

    # Aquí debería ir un parser robusto, pero por ahora hacemos uno simple.
    text = params.strip()

    await send_message("📩 Procesando señal manual…")

    try:
        # TODO: reemplazar en el futuro por un parser oficial
        parts = text.split()
        direction = parts[0].lower()
        symbol = parts[1].upper()

        temp_signal = {
            "symbol": symbol,
            "direction": direction,
            "entry": None,
            "tp_list": [],
            "sl": None,
        }

        await process_new_signal(temp_signal)

    except Exception as e:
        logger.error(f"❌ Error procesando señal manual: {e}")
        await send_message("❌ No se pudo procesar la señal.")
