"""
config.py
---------
Configuración central para Trading AI Monitor v2.

Incluye:
    ✔ Variables de entorno
    ✔ Paths absolutos
    ✔ Token y llaves
    ✔ Config de Bybit (main / testnet)
    ✔ Config de Telegram (Telethon + Bot)
    ✔ Config de Base de Datos
    ✔ Flags del motor técnico
"""

import os
from dotenv import load_dotenv

# ============================================================
# Cargar archivo .env
# ============================================================

load_dotenv()


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "data", "trading_ai.db")
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)


# ============================================================
# TELEGRAM — API DE USUARIO (TELETHON)
# ============================================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "trading_ai_monitor")

# Canal VIP donde llegan las señales
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", "0"))

# ============================================================
# TELEGRAM — BOT
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))


# ============================================================
# BYBIT — API CONFIGURACIÓN
# ============================================================

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

# Puede ser: "real" o "demo"
BYBIT_ENV = os.getenv("BYBIT_ENV", "real").lower()

# Endpoint automático según entorno
if BYBIT_ENV == "demo":
    BYBIT_ENDPOINT = "https://api-demo.bybit.com"
else:
    BYBIT_ENDPOINT = os.getenv("BYBIT_ENDPOINT", "https://api.bybit.com")

# Testnet opcional (legacy)
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

# Solo tradeamos futuros lineales
BYBIT_CATEGORY = "linear"
SIMULATION_MODE = False
TRADING_MODE = "REAL"  # o "DEMO"

# ============================================================
# FLAGS DEL SISTEMA
# ============================================================

# Modo de depuración para el motor técnico (imprime cálculos internos)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Alias de compatibilidad para motores viejos, por si algo lo usa
ANALYSIS_DEBUG_MODE = DEBUG_MODE

# services/telegram_service/command_bot.py
# --- versión async compatible con el loop global ---


async def start_command_bot():
    logger.info("🤖 Iniciando bot de comandos (LITE)…")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ⬇️ Handlers
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("analizar", analizar))
    app.add_handler(CommandHandler("reactivacion", reactivar))
    app.add_handler(CommandHandler("config", config_cmd))

    # ⬇️ Reemplaza run_polling() por control manual del ciclo
    await app.initialize()  # prepara todo
    await app.start()  # inicia conexión
    app.updater.start_polling()  # ⬅️ inicia el polling sin tocar el event loop

    logger.info("🤖 Bot de comandos listo (modo async).")

    return app  # ← retornamos la instancia para detenerla luego si se necesita


# ============================================================
# VALIDACIÓN RÁPIDA (para evitar errores en tiempo de ejecución)
# ============================================================


def validate_config():
    errors = []

    if API_ID == 0 or not API_HASH:
        errors.append("❌ TELEGRAM API_ID/API_HASH no configurados.")

    if TELEGRAM_CHANNEL_ID == 0:
        errors.append("❌ TELEGRAM_CHANNEL_ID no configurado.")

    if not TELEGRAM_BOT_TOKEN:
        errors.append("❌ TELEGRAM_BOT_TOKEN no configurado.")

    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        errors.append("❌ BYBIT API KEYS no configuradas.")

    if not os.path.exists(DB_PATH):
        errors.append(f"⚠️ Base de datos no encontrada en {DB_PATH} (se creará).")

    if errors:
        print("\n".join(errors))
        print("⚠️ Revisa tu archivo .env antes de continuar.\n")


# ============================================================
# EJECUCIÓN OPCIONAL (debug)
# ============================================================

if __name__ == "__main__":
    print("📘 Validando configuración...")
    validate_config()
    print("✔ Configuración OK.")

# Intervalo en minutos para revisar señales pendientes
SIGNAL_RECHECK_INTERVAL_MINUTES = 5

# Parámetros EMA usados por el motor técnico
EMA_SHORT_PERIOD = 10
EMA_MID_PERIOD = 30
EMA_LONG_PERIOD = 50

# Parámetros MACD usados por el motor técnico
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Modo de análisis del motor técnico
# Opciones: "normal" / "aggressive" / "conservative"
ANALYSIS_MODE = os.getenv("ANALYSIS_MODE", "normal")
