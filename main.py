"""
main.py — Punto de entrada unificado del Trading AI Monitor
"""

import asyncio
import logging

from core.logger_config import configure_logging
from core.database import init_db

# Servicios técnicos
from signals_service.signal_reactivation_sync import start_reactivation_loop
from positions_service.operation_tracker import start_operation_tracker
from positions_service.position_reversal_monitor import start_reversal_monitor

# Servicios de Telegram
from telegram_service.telegram_reader import start_telegram_reader
from telegram_service.command_bot import start_command_bot


async def main():

    # ---------------------------------------------------
    # 1) Configurar logging
    # ---------------------------------------------------
    configure_logging()
    logger = logging.getLogger("MAIN")
    logger.info("🚀 Trading AI Monitor iniciando...")

    # ---------------------------------------------------
    # 2) Inicializar DB
    # ---------------------------------------------------
    init_db()

    # ---------------------------------------------------
    # 3) Iniciar servicios Telegram (lector + bot)
    # ---------------------------------------------------
    logger.info("📡 Iniciando telegram_reader y command_bot...")
    reader_task = asyncio.create_task(start_telegram_reader())
    bot_task = asyncio.create_task(start_command_bot())

    # ---------------------------------------------------
    # 4) Iniciar servicios de análisis técnico
    # ---------------------------------------------------
    logger.info("🧠 Iniciando servicios técnicos...")

    reactivation_task = asyncio.create_task(start_reactivation_loop())
    operations_task = asyncio.create_task(start_operation_tracker())
    reversal_task = asyncio.create_task(start_reversal_monitor())

    logger.info("✅ Todos los servicios iniciados correctamente.")

    # ---------------------------------------------------
    # 5) Mantener servicios activos
    # ---------------------------------------------------
    await asyncio.gather(
        reader_task,
        bot_task,
        reactivation_task,
        operations_task,
        reversal_task,
    )


if __name__ == "__main__":
    asyncio.run(main())
