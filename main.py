import logging
import asyncio
import sys
from datetime import datetime
from telegram_reader import TelegramSignalReader
from command_bot import start_command_bot
from signal_manager import process_signal
from bybit_client import get_open_positions
from operation_tracker import monitor_open_positions
from database import init_database
from config import SIMULATION_MODE

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
# 🚀 Arranque principal del sistema
# ================================================================
async def main():
    mode = "signals"
    if len(sys.argv) > 1 and sys.argv[1] == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]
    logger.info("🚀 Iniciando Trading AI Monitor (modo simulación: %s)", SIMULATION_MODE)

    init_database()

    if mode == "signals":
        asyncio.create_task(TelegramSignalReader(callback=process_signal).start())
        asyncio.create_task(start_command_bot())  # ✅ así está bien
    elif mode == "monitor":
        positions = get_open_positions()
        if positions:
            asyncio.create_task(asyncio.to_thread(monitor_open_positions, positions))

    # 4️⃣ Recuperar posiciones abiertas y activar monitoreo
    logger.info("📡 Recuperando posiciones abiertas...")
    positions = get_open_positions()

    if positions:
        logger.info(f"🧭 {len(positions)} posiciones activas detectadas, iniciando monitoreo...")
        asyncio.create_task(asyncio.to_thread(monitor_open_positions, positions))
    else:
        logger.info("ℹ️ No hay posiciones abiertas actualmente.")

    # 5️⃣ Bucle principal de mantenimiento
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
