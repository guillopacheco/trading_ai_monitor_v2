"""
main.py — Punto de entrada del Trading AI Monitor
"""

import asyncio
import logging

from utils.logger import configure_logging
from services.telegram_service import start_telegram, client
from services.scheduler_service import start_scheduler


async def main():
    # ---------------------------------------------
    # 1) Configurar logging
    # ---------------------------------------------
    configure_logging()
    logger = logging.getLogger("MAIN")
    logger.info("🚀 Iniciando Trading AI Monitor...")

    # ---------------------------------------------
    # 2) Iniciar Telegram (usuario + bot)
    # ---------------------------------------------
    await start_telegram()
    logger.info("📡 Telegram iniciado.")

    # ---------------------------------------------
    # 3) Registrar Scheduler
    # ---------------------------------------------
    loop = asyncio.get_running_loop()
    await start_scheduler(loop)   # ✔ ESTE ERA EL ERROR
    logger.info("🕒 Scheduler registrado.")

    # ---------------------------------------------
    # 4) Mantener app ejecutándose
    # ---------------------------------------------
    logger.info("📡 Sistema en ejecución. Esperando eventos de Telegram...")
    await client.run_until_disconnected()


# ---------------------------------------------
# Ejecutar main()
# ---------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
