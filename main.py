"""
main.py — Punto de entrada unificado del Trading AI Monitor
"""

import asyncio
import logging
import threading

from telethon import TelegramClient
from config import API_ID, API_HASH, TELEGRAM_SESSION

from core.logger_config import configure_logging
from core.database import init_db

from services.signals_service.signal_reactivation_sync import start_reactivation_monitor
from services.positions_service.operation_tracker import start_operation_tracker
from services.positions_service.position_reversal_monitor import start_reversal_monitor

from services.telegram_service.telegram_reader import start_telegram_reader
from services.telegram_service.command_bot import start_command_bot


async def main():

    # ---------------------------------------------------
    # 1) Logging
    # ---------------------------------------------------
    configure_logging()
    logger = logging.getLogger("MAIN")
    logger.info("🚀 Trading AI Monitor iniciando...")

    # ---------------------------------------------------
    # 2) Base de datos
    # ---------------------------------------------------
    init_db()

    # ---------------------------------------------------
    # 3) Cliente Telegram (Telethon)
    # ---------------------------------------------------
    client = TelegramClient(
        TELEGRAM_SESSION,
        API_ID,
        API_HASH
    )
    await client.start()

    # ---------------------------------------------------
    # 4) Iniciar lector de señales
    # ---------------------------------------------------
    logger.info("📡 Iniciando telegram_reader...")
    reader_task = asyncio.create_task(start_telegram_reader(client))

    # ---------------------------------------------------
    # 5) Lanzar command_bot EN THREAD SEPARADO
    # ---------------------------------------------------
    logger.info("🤖 Iniciando command_bot en thread separado...")

    bot_thread = threading.Thread(
        target=start_command_bot,
        name="CommandBotThread",
        daemon=True
    )
    bot_thread.start()

    # ---------------------------------------------------
    # 6) Iniciar servicios técnicos
    # ---------------------------------------------------
    logger.info("🧠 Iniciando servicios técnicos...")

    reactivation_task = asyncio.create_task(start_reactivation_monitor())
    operations_task   = asyncio.create_task(start_operation_tracker())
    reversal_task     = asyncio.create_task(start_reversal_monitor())

    logger.info("✅ Todos los servicios iniciados correctamente.")

    # ---------------------------------------------------
    # 7) Mantener servicios activos
    # ---------------------------------------------------
    await asyncio.gather(
        reader_task,
        reactivation_task,
        operations_task,
        reversal_task
    )


if __name__ == "__main__":
    asyncio.run(main())
