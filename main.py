import logging
import asyncio
import sys
from datetime import datetime

from telegram_reader import start_telegram_reader
from signal_manager import process_signal
from bybit_client import get_open_positions
from operation_tracker import monitor_open_positions
from database import init_database
from config import SIMULATION_MODE
from command_bot import start_command_bot


# ================================================================
# 🧱 Configuración del logger global
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
# 🚀 Función principal
# ================================================================
async def main():
    logger.info(f"🚀 Iniciando Trading AI Monitor (modo simulación: {SIMULATION_MODE})")
    init_database()

    # Detectar modo desde argumentos (signals / monitor)
    mode = "signals"
    if len(sys.argv) > 2 and sys.argv[1] == "--mode":
        mode = sys.argv[2]

    # ================================================================
    # 1️⃣ Iniciar modo señales (lector + bot de comandos)
    # ================================================================
    if mode == "signals":
        logger.info("📡 Activando modo de análisis de señales...")

        # Telegram Reader (Telethon)
        asyncio.create_task(start_telegram_reader(callback=process_signal))

        # Bot de comandos (en hilo separado)
        start_command_bot()

    # ================================================================
    # 2️⃣ Iniciar modo monitoreo (operaciones abiertas)
    # ================================================================
    elif mode == "monitor":
        logger.info("📊 Activando modo monitoreo de operaciones...")
        positions = get_open_positions()
        if positions:
            asyncio.create_task(asyncio.to_thread(monitor_open_positions, positions))
        else:
            logger.info("ℹ️ No hay posiciones abiertas actualmente.")

    # ================================================================
    # 3️⃣ Mantener el sistema activo con logs cada 5 min
    # ================================================================
    while True:
        await asyncio.sleep(300)
        logger.info(f"⏳ Sistema activo — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")


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
