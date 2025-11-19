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

Todo bajo un diseño estable usando asyncio.
------------------------------------------------------------
"""

import logging
import asyncio
from datetime import datetime

from telethon import TelegramClient

from config import (
    API_ID,
    API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION,
    SIMULATION_MODE,
)

from logger_config import setup_logging
from database import init_database
from telegram_reader import start_telegram_reader
from command_bot import start_command_bot
from operation_tracker import monitor_open_positions
from position_reversal_monitor import monitor_reversals
from signal_reactivation_sync import auto_reactivation_loop


# ============================================================
# 📘 Configuración de logging global
# ============================================================

setup_logging()
logger = logging.getLogger("MAIN")


# ============================================================
# 🌐 Cliente de Telethon (lector de señales)
# ============================================================

def init_telegram_client() -> TelegramClient:
    """
    Crea el cliente Telethon con la sesión configurada en .env
    y autentica si es necesario.
    """
    logger.info("📡 Inicializando cliente de Telethon...")

    client = TelegramClient(
        TELEGRAM_SESSION,
        API_ID,
        API_HASH
    )
    client.connect()

    if not client.is_user_authorized():
        logger.warning("📲 Autenticación requerida — enviando código...")
        client.send_code_request(TELEGRAM_PHONE)
        code = input("🔐 Ingrese el código enviado por Telegram: ")
        client.sign_in(TELEGRAM_PHONE, code)

    return client


# ============================================================
# 🧠 Loop recurrente de monitoreo de operaciones (Bybit)
# ============================================================

async def loop_positions(interval_seconds: int = 60):
    """
    Revisa las posiciones abiertas cada X segundos.
    """
    logger.info("📡 Monitor de posiciones iniciado (loop_positions).")

    while True:
        try:
            await monitor_open_positions()
        except Exception as e:
            logger.error(f"❌ Error en loop_positions: {e}")

        await asyncio.sleep(interval_seconds)


# ============================================================
# 🧠 Loop recurrente de reversión (cada X minutos)
# ============================================================

async def loop_reversals(interval_seconds: int = 300):
    """
    Monitor de reversiones profundas.
    """
    logger.info("🔍 Monitor de reversiones iniciado (loop_reversals).")

    while True:
        try:
            await monitor_reversals(run_once=True)
        except Exception as e:
            logger.error(f"❌ Error en loop_reversals: {e}")

        await asyncio.sleep(interval_seconds)


# ============================================================
# 🚀 Orquestador principal
# ============================================================

async def main():
    logger.info(f"🚀 Iniciando Trading AI Monitor (simulación: {SIMULATION_MODE})")

    # 1) Base de datos
    init_database()
    logger.info("🗄 Base de datos inicializada.")

    # 2) Cliente de Telethon
    telegram_client = init_telegram_client()

    # 3) Lector del canal VIP
    start_telegram_reader(telegram_client)
    logger.info("📩 Lector de señales activado.")

    # 4) Bot de comandos
    bot_task = asyncio.create_task(start_command_bot())
    logger.info("🤖 Bot de comandos iniciado.")

    # 5) Loop de monitoreo de posiciones
    positions_task = asyncio.create_task(loop_positions(60))

    # 6) Loop de detección de reversiones
    reversals_task = asyncio.create_task(loop_reversals(300))

    # 7) Loop de reactivación automática
    reactivation_task = asyncio.create_task(auto_reactivation_loop())

    logger.info("🧠 Tareas principales en ejecución.")
    logger.info("📡 Ejecutando cliente de Telegram...")

    # 8) Telethon mantiene el proceso vivo
    try:
        telegram_client.run_until_disconnected()

    finally:
        logger.warning("🛑 Cliente de Telegram desconectado. Finalizando sistema...")

        # Cancelar tareas activas
        for task in [
            bot_task,
            positions_task,
            reversals_task,
            reactivation_task
        ]:
            if task and not task.done():
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
        logger.error(f"❌ Error fatal en main.py: {e}")
