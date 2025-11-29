"""
main.py
-------
Punto de entrada oficial de la aplicación Trading AI Monitor.
"""

import asyncio
import logging

from services.telegram_service import (
    start_telegram_service,
    get_client,
)

from services.scheduler_service import start_scheduler
from services import db_service


# ============================================================
# LOGGING
# ============================================================

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("telethon").setLevel(logging.WARNING)


# ============================================================
# APP START
# ============================================================

async def main():
    configure_logging()
    logger = logging.getLogger("MAIN")

    logger.info("🚀 Iniciando Trading AI Monitor...")

    # ---------------------------
    # DB INIT
    # ---------------------------
    db_service.init_db()
    logger.info("🗄 Base de datos lista.")

    # ---------------------------
    # TELEGRAM SERVICE INIT
    # ---------------------------
    await start_telegram_service()
    logger.info("🤖 Servicio de Telegram iniciado.")

    # ---------------------------
    # SCHEDULER INIT (REACTIVACIÓN + POSICIONES)
    # ---------------------------
    await start_scheduler()
    logger.info("🕒 Scheduler activo.")

    # ---------------------------
    # TELETHON MAIN LOOP
    # ---------------------------
    client = get_client()
    logger.info("📡 Esperando eventos de Telegram...")
    await client.run_until_disconnected()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
