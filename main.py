"""
main.py — Fase 4 (2025)
Arranque maestro del Trading AI Monitor v2
Orquestación completa:
- Logging
- Base de datos
- ApplicationLayer
- CommandBot
- TelegramReader
- ReactivationSync
"""

import asyncio
import logging

from core.logger_config import configure_logging
from services.database import init_db

from application_layer import ApplicationLayer
from services.telegram_service.command_bot import start_command_bot
from services.telegram_service.telegram_reader import start_telegram_reader
from services.signals_service.signal_reactivation_sync import start_reactivation_monitor

logger = logging.getLogger("MAIN")


# ===========================================================
# 🎯 Tarea principal
# ===========================================================
async def main():
    # Inicializar logging
    configure_logging()
    logger.info("🚀 Trading AI Monitor iniciando...")

    # Inicializar base de datos global
    Database().init()
    logger.info("✅ Base de datos inicializada correctamente.")

    # Inicializar ApplicationLayer
    app_layer = ApplicationLayer()

    logger.info("📡 Iniciando servicios…")

    # Bot de comandos (modo embebido)
    command_task = asyncio.create_task(start_command_bot())

    # Lector de señales desde Telegram VIP
    reader_task = asyncio.create_task(start_telegram_reader())

    # Monitor de reactivación automática
    reactivation_task = asyncio.create_task(start_reactivation_monitor())

    logger.info("✅ Todos los servicios iniciados.")

    # Mantener servicios vivos
    await asyncio.gather(
        command_task,
        reader_task,
        reactivation_task
    )


# ===========================================================
# 🚀 Punto de entrada
# ===========================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.getLogger("MAIN").exception(f"❌ Error crítico: {e}")
