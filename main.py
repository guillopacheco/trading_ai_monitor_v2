"""
main.py — Orquestador FINAL (versión integrada 2025-11)
------------------------------------------------------------
Inicializa y ejecuta TODOS los módulos del sistema:

✔ Base de datos
✔ Cliente de Telethon
✔ Lector de señales (telegram_reader)
✔ Bot de comandos (command_bot)
✔ Monitor de operaciones (operation_tracker)
✔ Monitor de reversiones (position_reversal_monitor)
✔ Reactivación automática de señales (signal_reactivation_sync)

Todo corriendo en asyncio sin bloqueos.
------------------------------------------------------------
"""

import logging
import asyncio
import sys
from datetime import datetime

from telethon import TelegramClient
from config import (
    API_ID,
    API_HASH,
    TELEGRAM_PHONE,
    SIMULATION_MODE,
)

from database import init_database
from telegram_reader import start_telegram_reader
from command_bot import start_command_bot
from operation_tracker import monitor_open_positions
from position_reversal_monitor import monitor_reversals
from signal_reactivation_sync import auto_reactivation_loop
from logger_config import setup_logging


# ============================================================
# 📘 Configuración de logging
# ============================================================
setup_logging()
logger = logging.getLogger("__main__")


# ============================================================
# 🌐 Cliente de Telethon (lector de señales)
# ============================================================
def init_telegram_client():
    """
    Inicializa un cliente de Telethon y realiza la autenticación
    si es necesario.
    """
    client = TelegramClient("monitor_session", API_ID, API_HASH)

    client.connect()

    if not client.is_user_authorized():
        logger.warning("📲 Autenticación de Telegram requerida. Enviando código...")
        client.send_code_request(TELEGRAM_PHONE)
        code = input("🔐 Ingrese el código enviado por Telegram: ")
        client.sign_in(TELEGRAM_PHONE, code)

    return client


# ============================================================
# 🧠 Bucle independiente de monitoreo recurrente
# ============================================================
async def loop_positions(interval_seconds=60):
    """
    Monitor de operaciones abiertas cada 60s.
    (operation_tracker trabaja en to_thread).
    """
    while True:
        try:
            await asyncio.to_thread(monitor_open_positions)
        except Exception as e:
            logger.error(f"❌ Error en loop_positions: {e}")
        await asyncio.sleep(interval_seconds)


# ============================================================
# 🚀 Orquestador principal
# ============================================================
async def main():
    logger.info(f"🚀 Iniciando Trading AI Monitor (modo simulación: {SIMULATION_MODE})")

    # 1) Base de datos
    init_database()

    # 2) Lector de Telethon
    telegram_client = init_telegram_client()

    # 3) Iniciar listener de señales
    start_telegram_reader(telegram_client)

    # 4) Iniciar bot de comandos (async)
    bot_task = asyncio.create_task(start_command_bot())

    # 5) Iniciar monitor de posiciones cada 60s
    positions_task = asyncio.create_task(loop_positions(60))

    # 6) Monitor de reversiones (cada 5 min)
    reversals_task = asyncio.create_task(monitor_reversals(interval_seconds=300))

    # 7) Reactivación automática de señales (cada 15 min)
    reactivation_task = asyncio.create_task(auto_reactivation_loop())

    logger.info("🧠 Tareas principales iniciadas.")
    logger.info("📡 Conectando cliente de Telegram...")

    # 8) Iniciar Telethon (bloquea, pero compatible con asyncio)
    try:
        telegram_client.run_until_disconnected()
    finally:
        logger.warning("🛑 Cliente de Telegram desconectado. Cerrando sistema...")

        # Cancelar tareas activas
        for task in [bot_task, positions_task, reversals_task, reactivation_task]:
            if not task.done():
                task.cancel()

        logger.info("🧹 Sistema finalizado limpiamente.")


# ============================================================
# 🔧 Entrada principal
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Ejecución detenida manualmente.")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
