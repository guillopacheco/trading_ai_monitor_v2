"""
main.py
-------
Archivo principal del sistema. Orquesta la inicialización
de servicios, Telegram, router y scheduler.
"""

import asyncio
import logging

from utils.logger import configure_logging
from services.telegram_service import start_telegram, client
from services.scheduler_service import start_scheduler

# 🔵 IMPORTA EL ROUTER (MUY IMPORTANTE)
import controllers.telegram_router  # ← registra handlers al cargar


logger = logging.getLogger("MAIN")


async def main():
    configure_logging()
    logger.info("🚀 Iniciando Trading AI Monitor...")

    # 1. Telegram
    await start_telegram()

    # 2. Scheduler (loops)
    await start_scheduler()

    logger.info("📡 Sistema en ejecución. Esperando eventos de Telegram...")

    # Mantener la app viva con el loop de Telethon
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
