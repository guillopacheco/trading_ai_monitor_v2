import logging
import asyncio
import sys
from datetime import datetime
from database import init_database
from config import SIMULATION_MODE
from telegram_reader import start_telegram_reader
from signal_manager import process_signal
from bybit_client import get_open_positions
from operation_tracker import monitor_open_positions
from command_bot import start_command_bot

# ================================================================
# 🧱 Configuración de logging global
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
# 🚀 Función principal (loop global estable)
# ================================================================
async def main():
    logger.info(f"🚀 Iniciando Trading AI Monitor (modo simulación: {SIMULATION_MODE})")

    # 1️⃣ Inicializar base de datos
    init_database()

    # 2️⃣ Determinar modo de ejecución
    mode = "signals"
    if len(sys.argv) > 2 and sys.argv[1] == "--mode":
        mode = sys.argv[2]

    # 3️⃣ Obtener posiciones abiertas (para el modo monitor)
    logger.info("📡 Recuperando posiciones abiertas...")
    positions = get_open_positions()

    # 4️⃣ Crear tareas concurrentes
    tasks = []

    # 🧠 Lector de señales (Telethon)
    if mode == "signals":
        logger.info("📡 Activando modo de análisis de señales...")
        tasks.append(asyncio.create_task(start_telegram_reader(callback=process_signal)))

    # 🤖 Bot de comandos Telegram
    tasks.append(asyncio.create_task(start_command_bot()))

    # 💹 Monitoreo de operaciones abiertas
    if positions:
        logger.info(f"🧭 {len(positions)} posiciones activas detectadas, iniciando monitoreo...")
        tasks.append(asyncio.to_thread(monitor_open_positions, positions))
    else:
        logger.info("ℹ️ No hay posiciones abiertas actualmente.")

    # 5️⃣ Mantener el sistema activo permanentemente
    try:
        while True:
            await asyncio.sleep(300)
            logger.info(f"⏳ Sistema activo — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except asyncio.CancelledError:
        logger.warning("🛑 Bucle principal cancelado.")
    except Exception as e:
        logger.error(f"❌ Error crítico en main(): {e}")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        logger.info("🧹 Tareas limpiadas. Finalizando sistema.")


# ================================================================
# 🏁 Punto de entrada
# ================================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Ejecución detenida manualmente.")
    except Exception as e:
        logger.error(f"❌ Error fatal en ejecución: {e}")
