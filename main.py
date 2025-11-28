"""
main.py
-------
Punto de entrada oficial de Trading AI Monitor v2.

Esta versión es totalmente modular:
    - Servicios
    - Controladores
    - Listeners
    - Monitores via Scheduler
    - TelegramService administrado de forma centralizada

NO contiene lógica técnica, ni DB, ni Bybit.
Solo inicia los servicios y mantiene la app viva.
"""

import asyncio
import logging
from logging.handlers import RotatingFileHandler

# Servicios y controladores
from services.telegram_service import (
    start_signal_listener,
    start_command_listener,
)

from controllers.signal_listener import on_new_signal
from controllers.commands_controller import handle_command
from services.scheduler_service import scheduler


# ============================================================
# 🔵 Configuración global de logging
# ============================================================
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Consola
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    # Archivo rotativo
    handler = RotatingFileHandler(
        "trading_ai.log", maxBytes=5_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    logging.info("📘 Logging configurado correctamente.")


# ============================================================
# 🔵 Arranque principal
# ============================================================
async def main():
    setup_logging()
    logging.info("🚀 Iniciando Trading AI Monitor v2…")

    # ========================================================
    # 1. INICIAR LISTENER DE SEÑALES VIP
    # ========================================================
    logging.info("📡 Activando listener de señales VIP…")
    asyncio.create_task(start_signal_listener(on_new_signal))

    # ========================================================
    # 2. INICIAR LISTENER DE COMANDOS DEL BOT
    # ========================================================
    logging.info("🤖 Activando listener de comandos…")
    asyncio.create_task(start_command_listener(handle_command))

    # ========================================================
    # 3. ACTIVAR MONITORES POR DEFECTO
    # ========================================================
    logging.info("🧠 Activando monitores iniciales…")

    # Monitor de posiciones
    await scheduler.start_monitor("positions")

    # Monitor de reactivaciones (si está implementado)
    if "reactivations" in scheduler.monitors:
        await scheduler.start_monitor("reactivations")

    # ========================================================
    # 4. Mantener la app viva
    # ========================================================
    logging.info("📡 Sistema operativo. Esperando eventos…")

    # Mantiene la aplicación viva para Telethon & tasks async
    while True:
        await asyncio.sleep(3600)


# ============================================================
# 🔵 EJECUCIÓN PRINCIPAL
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario.")
