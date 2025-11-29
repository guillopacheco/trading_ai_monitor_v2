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


async def main():
    # Configurar logging
    configure_logging()
    logger = logging.getLogger("MAIN")

    logger.info("🚀 Iniciando Trading AI Monitor...")

    # Obtener loop actual
    loop = asyncio.get_running_loop()

    # Iniciar Telegram (usuario + bot)
    await start_telegram()
    logger.info("📡 Telegram iniciado.")

    # Iniciar scheduler (reactivación + posiciones)
    start_scheduler(loop)
    logger.info("🕒 Scheduler registrado.")

    logger.info("📡 Sistema en ejecución. Esperando eventos de Telegram...")

    # Mantener app viva
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
