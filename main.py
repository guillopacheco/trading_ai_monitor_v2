"""
main.py
---------------------------------------------------------
Punto de entrada principal del sistema Trading AI Monitor.
Inicia:
1️⃣ Lector de señales de Telegram (canal de señales)
2️⃣ Bot de comandos de Telegram (interactivo)
3️⃣ Monitoreo de operaciones abiertas en Bybit
---------------------------------------------------------
"""

import logging
import asyncio
import sys
from datetime import datetime

from telegram_reader import start_telegram_reader
from command_bot import start_command_bot
from signal_manager import process_signal
from bybit_client import get_open_positions
from operation_tracker import monitor_open_positions
from database import init_database
from config import SIMULATION_MODE

# ================================================================
# 🧱 Configuración global del logger
# ================================================================
LOG_FILE = "trading_ai_monitor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("__main__")


# ================================================================
# 🚀 Proceso principal
# ================================================================
async def main():
    """
    Lógica central:
    - Inicia el bot de señales (Telethon)
    - Inicia el bot de comandos
    - Lanza el monitoreo de operaciones abiertas
    """

    # Detectar modo
    mode = "signals"
    if len(sys.argv) > 1 and sys.argv[1] == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]

    logger.info(f"🚀 Iniciando Trading AI Monitor (modo simulación: {SIMULATION_MODE})")

    # ============================================================
    # Inicializar base de datos
    # ============================================================
    init_database()

    # ============================================================
    # Iniciar lector de señales y bot de comandos
    # ============================================================
    if mode == "signals":
        logger.info("📡 Activando modo de análisis de señales...")
        # Lector de Telegram (Telethon)
        asyncio.create_task(start_telegram_reader(callback=process_signal))
        # Bot de comandos (python-telegram-bot)
        asyncio.create_task(start_command_bot())

    elif mode == "monitor":
        logger.info("📊 Modo monitoreo de operaciones activado...")
        positions = get_open_positions()
        if positions:
            asyncio.create_task(asyncio.to_thread(monitor_open_positions, positions))

    # ============================================================
    # Recuperar posiciones abiertas para monitoreo
    # ============================================================
    logger.info("📡 Recuperando posiciones abiertas...")
    positions = get_open_positions()

    if positions:
        logger.info(f"🧭 {len(positions)} posiciones activas detectadas, iniciando monitoreo...")
        asyncio.create_task(asyncio.to_thread(monitor_open_positions, positions))
    else:
        logger.info("ℹ️ No hay posiciones abiertas actualmente.")

    # ============================================================
    # Bucle principal de mantenimiento
    # ============================================================
    while True:
        await asyncio.sleep(300)
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        logger.info(f"⏳ Sistema activo — {now_str}")


# ================================================================
# 🏁 Punto de entrada
# ================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Ejecución detenida manualmente.")
    except Exception as e:
        logger.error(f"❌ Error crítico en main(): {e}")
