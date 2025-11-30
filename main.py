"""
main.py
-------
Punto de entrada de la aplicación Trading AI Monitor.
"""

from __future__ import annotations
import asyncio
import logging

from utils.logger import configure_logging
from services.telegram_service import start_telegram
from services.scheduler_service import start_scheduler
from services.db_service import init_db  # ← NECESARIO


async def main():
    # Configurar logging
    configure_logging()
    logger = logging.getLogger("MAIN")

    logger.info("🚀 Iniciando Trading AI Monitor...")

    # 🔧 Crear tablas si no existen
    init_db()

    # Obtener loop actual
    loop = asyncio.get_running_loop()

    # Iniciar Telegram
    await start_telegram()
    logger.info("📡 Telegram iniciado.")

    # Iniciar scheduler (reactivación + posiciones)
    start_scheduler(loop)
    logger.info("🕒 Scheduler registrado.")

    logger.info("📡 Sistema en ejecución. Esperando eventos de Telegram...")

    # Mantener la app viva
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
