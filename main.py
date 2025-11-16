"""
main.py — Orquestador
- Inicializa DB
- Lanza lector de Telegram (telegram_reader.start_telegram_reader)
- Lanza bot de comandos (command_bot.start_command_bot)
- Lanza monitor de posiciones (operation_tracker.monitor_open_positions)
"""

import logging
import asyncio
import sys
from datetime import datetime
from database import init_database
from config import SIMULATION_MODE
from telegram_reader import start_telegram_reader  # Debe internamente llamar a process_signal
from command_bot import start_command_bot
from operation_tracker import monitor_open_positions
from signal_reactivation_sync import auto_reactivation_loop
from position_reversal_monitor import monitor_reversals  # 👈 importar el módulo
from signal_reactivation_sync import auto_reactivation_loop
from logger_config import setup_logging
setup_logging()


LOG_FILE = "trading_ai_monitor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)

logger = logging.getLogger("__main__")

async def main():
    logger.info(f"🚀 Iniciando Trading AI Monitor (modo simulación: {SIMULATION_MODE})")
    init_database()

    # Modo (por si deseas variantes)
    mode = "signals"
    if len(sys.argv) > 2 and sys.argv[1] == "--mode":
        mode = sys.argv[2]

    tasks = []

    # Lector de Telegram (señales)
    if mode == "signals":
        tasks.append(asyncio.create_task(start_telegram_reader()))

    # Bot de comandos
    tasks.append(asyncio.create_task(start_command_bot()))

    # Monitor de posiciones (asíncrono)
    tasks.append(asyncio.create_task(monitor_open_positions(poll_seconds=60)))

    # 🧠 Monitor de posibles reversiones técnicas (cada 5 min)
    tasks.append(asyncio.create_task(monitor_reversals(interval_seconds=300)))

    # ♻️ Reactivación automática de señales
    try:
        asyncio.create_task(auto_reactivation_loop(900))  # cada 15 min
        logger.info("♻️ Reactivación automática de señales habilitada (intervalo: 15 min).")
    except Exception as e:
        logger.error(f"❌ No se pudo iniciar el módulo de reactivación automática: {e}")

    try:
        while True:
            await asyncio.sleep(300)
            logger.info(f"⏳ Sistema activo — {datetime.now():%Y-%m-%d %H:%M:%S}")
    except asyncio.CancelledError:
        logger.warning("🛑 Bucle principal cancelado.")
    except Exception as e:
        logger.error(f"❌ Error crítico en main(): {e}")
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        logger.info("🧹 Tareas limpiadas. Finalizando sistema.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Ejecución detenida manualmente.")
    except Exception as e:
        logger.error(f"❌ Error fatal en ejecución: {e}")