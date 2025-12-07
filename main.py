"""
main.py — versión final estable, bot funcionando.
"""

import asyncio
import logging

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
    configure_logging()
    logger = logging.getLogger("MAIN")
    logger.info("🚀 Trading AI Monitor iniciando...")

    init_db()

    # Telethon
    client = TelegramClient(TELEGRAM_SESSION, API_ID, API_HASH)
    await client.start()

    logger.info("📡 Iniciando servicios…")

    # 🔥 Bot de comandos en TASK paralela (NO await)
    asyncio.create_task(start_command_bot())

    # Telegram reader (Telethon)
    reader_task = asyncio.create_task(start_telegram_reader(client))

    # Servicios
    reactivation_task = asyncio.create_task(start_reactivation_monitor())
    operations_task   = asyncio.create_task(start_operation_tracker())
    reversal_task     = asyncio.create_task(start_reversal_monitor())

    logger.info("✅ Todos los servicios iniciados.")

    await asyncio.gather(
        reader_task,
        reactivation_task,
        operations_task,
        reversal_task,
    )


if __name__ == "__main__":
    asyncio.run(main())
