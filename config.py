"""
config.py — versión final integrada
Lee automáticamente .env y mantiene ABSOLUTAMENTE TODAS
las configuraciones del sistema antiguo + compatibilidad con módulos nuevos.
"""

import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# ================================================================
# 📂 TELEGRAM — API de usuario (Telethon) y BOT
# ================================================================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "trading_ai_monitor")

# Canal VIP donde llegan las señales
TELEGRAM_CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", "0"))

# Bot privador (para enviar análisis, alertas, /estado, etc.)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))


# ================================================================
# 💹 BYBIT API
# ================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BYBIT_ENV = os.getenv("BYBIT_ENV", "real").lower()

if BYBIT_ENV == "demo":
    BYBIT_ENDPOINT = "https://api-demo.bybit.com"
else:
    BYBIT_ENDPOINT = os.getenv("BYBIT_ENDPOINT", "https://api.bybit.com")

BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
BYBIT_CATEGORY = "linear"


# ================================================================
# ⚙️ GENERAL
# ================================================================
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"
APP_MODE = os.getenv("APP_MODE", "ANALYSIS")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_PATH = os.getenv("DATABASE_FILE", "trading_ai_monitor.db")


# ================================================================
# 🎚 Sensibilidad del motor de análisis (technical_brain)
# ================================================================
ANALYSIS_MODE = os.getenv("ANALYSIS_MODE", "balanced")  # aggressive | balanced | conservative

MIN_BARS_STRONG_TF = 120
WICK_FILTER_ENABLED = True
WICK_RATIO_THRESHOLD = 2.5  # > 2 = velas con mechas largas


# ================================================================
# ⚙️ APALANCAMIENTO Y RIESGO
# ================================================================
LEVERAGE = int(os.getenv("LEVERAGE", 20))
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", 20))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.05))
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", 0.1))
ACCOUNT_BALANCE = float(os.getenv("ACCOUNT_BALANCE", 1000))


# ================================================================
# 💰 UMBRALES DE ROI (gestión de pérdidas)
# ================================================================
ROI_REVERSION_THRESHOLD = float(os.getenv("ROI_REVERSION_THRESHOLD", -30))
ROI_DYNAMIC_STOP_THRESHOLD = float(os.getenv("ROI_DYNAMIC_STOP_THRESHOLD", 60))
ROI_TAKE_PROFIT_THRESHOLD = float(os.getenv("ROI_TAKE_PROFIT_THRESHOLD", 100))
ROI_PARTIAL_CLOSE_PERCENT = float(os.getenv("ROI_PARTIAL_CLOSE_PERCENT", 70))


# ================================================================
# 📊 Configuración de indicadores
# ================================================================
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ATR_PERIOD = 14
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

DEFAULT_TIMEFRAMES = ["1", "5", "15"]


# ================================================================
# ⏱️ Intervalos
# ================================================================
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400

REVIEW_INTERVAL_NORMAL = 900      # 15 min
REVIEW_INTERVAL_HIGH_VOL = 300    # 5 min
MAX_WAIT_TIME = 24 * SECONDS_IN_HOUR
EXTENDED_MONITORING_TIMEOUT = 72 * SECONDS_IN_HOUR

SIGNAL_RECHECK_INTERVAL_MINUTES = int(os.getenv("SIGNAL_RECHECK_INTERVAL_MINUTES", 15))


# ================================================================
# 📈 Condiciones extendidas
# ================================================================
EXTENDED_MONITORING_CONDITIONS = {
    "min_atr_multiplier": 1.3,
    "max_price_deviation": 0.15,
    "rsi_extreme_threshold": 25,
    "weekend_extension_hours": 48
}


# ================================================================
# 🔁 Umbrales de reactivación
# ================================================================
REACTIVATION_THRESHOLDS = {
    "confirmation_min_match": 60,
    "price_proximity": 0.08,
    "volatility_increase": 1.2
}


# ================================================================
# 🧪 Validación
# ================================================================
def validate_config():
    missing = []

    if not API_ID: missing.append("TELEGRAM_API_ID")
    if not API_HASH: missing.append("TELEGRAM_API_HASH")
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_USER_ID: missing.append("TELEGRAM_USER_ID")
    if not TELEGRAM_CHANNEL_ID: missing.append("TELEGRAM_CHANNEL_ID")

    if missing:
        raise ValueError(f"⚠️ VARIABLES FALTANTES: {', '.join(missing)}")

    print(f"✅ Config validado | Entorno: {BYBIT_ENV.upper()}")
    print(f"🌍 Endpoint: {BYBIT_ENDPOINT}")


if __name__ == "__main__":
    validate_config()

ANALYSIS_DEBUG_MODE = True

# Alias para compatibilidad con el motor técnico unificado
DEBUG_MODE = ANALYSIS_DEBUG_MODE
DEBUG_MODE = True
