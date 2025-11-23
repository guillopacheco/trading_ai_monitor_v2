"""
main.py — Orquestador FINAL con integración de alertas (2025-11)

Incluye:
✔ Alertas tempranas de reversión (integradas en motor_wrapper + trackers)
✔ Alertas de agotamiento de tendencia (operation_tracker)
✔ Alertas automáticas de TP (operation_tracker)
✔ Sin modificar módulos externos
✔ Sin romper compatibilidad
"""

import logging
import asyncio

from telethon import TelegramClient

from config import (
    API_ID,
    API_HASH,
    TELEGRAM_PHONE,
    TELEGRAM_SESSION,
    SIMULATION_MODE,
)

from logger_config import setup_logging
from database import init_database
from telegram_reader import start_telegram_reader
from command_bot import start_command_bot
from operation_tracker import monitor_open_positions
from position_reversal_monitor import monitor_reversals
from signal_reactivation_sync import auto_reactivation_loop


# ============================================================
# 📘 Configuración global de logging
# ============================================================

setup_logging()
logger = logging.getLogger("MAIN")


# ============================================================
# 🌐 Cliente de Telethon
# ============================================================

async def init_telegram_client() -> TelegramClient:
    """
    Inicializa el cliente de Telethon de forma segura.
    Maneja autenticación si la sesión no ha sido autorizada.
    """
    logger.info("📡 Inicializando cliente Telethon...")

    client = TelegramClient(
        TELEGRAM_SESSION,
        API_ID,
        API_HASH,
    )

    await client.connect()

    if not await client.is_user_authorized():
        logger.warning("📲 Autenticación requerida. Enviando código...")
        await client.send_code_request(TELEGRAM_PHONE)
        code = input("🔐 Ingrese el código enviado por Telegram: ")
        await client.sign_in(TELEGRAM_PHONE, code)

    return client


# ============================================================
# 📊 Loop — Monitoreo general de operaciones Bybit + TP alerts
# ============================================================

async def loop_positions(interval_seconds: int = 60):
    logger.info("📡 Iniciando monitor de posiciones (loop_positions)")
    while True:
        try:
            # Aquí ya están integrados:
            # ✔ Alertas automáticas de TP
            # ✔ Alertas de agotamiento
            # ✔ Alertas tempranas de reversión
            await monitor_open_positions()
        except Exception as e:
            logger.error(f"❌ Error en loop_positions: {e}")

        await asyncio.sleep(interval_seconds)


# ============================================================
# 🔥 Loop — Reversiones profundas (motor_wrapper)
# ============================================================

async def loop_reversals(interval_seconds: int = 300):
    logger.info("🔍 Reversal monitor iniciado (loop_reversals)")
    while True:
        try:
            # Aquí se evalúan:
            # ✔ Reversiones mayores (-50%)
            # ✔ Posibles reversiones basadas en smart bias + divergencias
            await monitor_reversals(run_once=True)
        except Exception as e:
            logger.error(f"❌ Error en loop_reversals: {e}")

        await asyncio.sleep(interval_seconds)


# ============================================================
# 🚀 MAIN — Orquestación central del sistema
# ============================================================

async def main():
    logger.info(f"🚀 Iniciando Trading AI Monitor (simulación: {SIMULATION_MODE})")

    # 1) Base de datos
    init_database()
    logger.info("🗄 Base de datos OK.")

    # 2) Telegram
    telegram_client = await init_telegram_client()

    # 3) Listener del canal VIP
    start_telegram_reader(telegram_client)
    logger.info("📩 Lector de señales activo.")

    # 4) Bot de comandos
    bot_task = asyncio.create_task(start_command_bot())
    logger.info("🤖 Bot Telegram listo.")

    # 5) Monitoreo de operaciones (incluye TPs + agotamiento + reversión temprana)
    positions_task = asyncio.create_task(loop_positions(60))

    # 6) Reversiones profundas
    reversals_task = asyncio.create_task(loop_reversals(300))

    # 7) Reactivación automática de señales
    reactivation_task = asyncio.create_task(auto_reactivation_loop())

    logger.info("🧠 Tareas del sistema en ejecución.")
    logger.info("📡 Esperando eventos de Telegram...")

    try:
        await telegram_client.run_until_disconnected()

    finally:
        logger.warning("🛑 Telegram desconectado. Cancelando tareas...")

        for t in [bot_task, positions_task, reversals_task, reactivation_task]:
            if t and not t.done():
                t.cancel()

        logger.info("🧹 Sistema finalizado limpiamente.")


# ============================================================
# 🏁 Entrada principal
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Interrumpido manualmente.")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
