import logging
import asyncio
import sys
from datetime import datetime, timezone
from telegram_reader import start_telegram_reader
from command_bot import start_command_bot_blocking
from signal_manager import process_signal
from bybit_client import get_open_positions
from operation_tracker import monitor_open_positions
from database import init_database
from config import SIMULATION_MODE

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

async def main():
    mode = "signals"
    if len(sys.argv) > 1 and sys.argv[1] == "--mode" and len(sys.argv) > 2:
        mode = sys.argv[2]
    logger.info("🚀 Iniciando Trading AI Monitor (modo simulación: %s)", SIMULATION_MODE)

    init_database()

    # 1) Lector del canal (Telethon) – dentro del loop principal
    asyncio.create_task(start_telegram_reader())

    # 2) Bot de comandos – en hilo dedicado con su propio loop
    asyncio.create_task(asyncio.to_thread(start_command_bot_blocking))

    # 3) (Opcional) Modo monitor: si quieres iniciar monitoreo al arrancar
    if mode == "monitor":
        positions = get_open_positions()
        if positions:
            asyncio.create_task(asyncio.to_thread(monitor_open_positions, positions))

    # 4) Log de “heartbeat”
    while True:
        await asyncio.sleep(300)
        logger.info(f"⏳ Sistema activo — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Ejecución detenida manualmente.")
    except Exception as e:
        logger.error(f"❌ Error crítico en main(): {e}")
