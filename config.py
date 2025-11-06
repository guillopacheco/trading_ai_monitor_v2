"""
Configuración centralizada de entorno y sistema
"""
import os
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

# ================================================================
# 🤖 TELEGRAM
# ================================================================
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "trading_ai_monitor")
TELEGRAM_SIGNAL_CHANNEL_ID = os.getenv("TELEGRAM_SIGNAL_CHANNEL_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")

# ================================================================
# 💹 BYBIT
# ================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BYBIT_CATEGORY = "linear"
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "true").lower() == "true"
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"

# Endpoint según entorno
BYBIT_BASE_URL = (
    "https://api-testnet.bybit.com" if BYBIT_TESTNET else "https://api.bybit.com"
)

# ================================================================
# ⚙️ CONFIGURACIÓN GENERAL
# ================================================================
APP_MODE = os.getenv("APP_MODE", "ANALYSIS")  # ANALYSIS o TRADING
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/trading_signals.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ================================================================
# 🧠 VALIDACIÓN
# ================================================================
def validate_config():
    missing = []
    for var in [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_USER_ID",
        "BYBIT_API_KEY",
        "BYBIT_API_SECRET",
    ]:
        if not globals().get(var):
            missing.append(var)
    if missing:
        print(f"⚠️  Faltan variables críticas en .env: {', '.join(missing)}")
    else:
        print("✅ Configuración validada correctamente.")

if __name__ == "__main__":
    validate_config()
