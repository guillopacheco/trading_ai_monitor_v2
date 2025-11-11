"""
config.py
------------------------------------------------------------
Archivo centralizado de configuración global del sistema.

Contiene todas las variables y parámetros operativos usados por:
- Telegram (cliente y bot)
- Bybit (API pública y privada)
- Gestión de riesgo, ROI y apalancamiento
- Ajustes de indicadores y análisis técnico
- Modo simulación / testnet
------------------------------------------------------------
"""

import os
from dotenv import load_dotenv

# ================================================================
# 📂 Cargar variables de entorno desde .env
# ================================================================
load_dotenv()

# ================================================================
# 🔐 Telegram - Usuario y Bot
# ================================================================
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "trading_ai_monitor")

# Canal desde donde se leen las señales (por ejemplo NeuroTrader)
TELEGRAM_SIGNAL_CHANNEL_ID = os.getenv("TELEGRAM_SIGNAL_CHANNEL_ID")

# Bot que envía las notificaciones
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")

# ================================================================
# 💹 Bybit API
# ================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# Entorno operativo: "real" o "demo"
BYBIT_ENV = os.getenv("BYBIT_ENV", "real").lower()

# Endpoint según entorno
if BYBIT_ENV == "demo":
    BYBIT_ENDPOINT = "https://api-demo.bybit.com"
else:
    BYBIT_ENDPOINT = "https://api.bybit.com"

# True si deseas usar testnet
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

# Categoría de mercado (linear, inverse, spot)
BYBIT_CATEGORY = "linear"

# ================================================================
# ⚙️ Configuración general
# ================================================================
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"
APP_MODE = os.getenv("APP_MODE", "ANALYSIS")  # ANALYSIS o TRADING
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_PATH = "data/trading_signals.db"

# ================================================================
# ⚙️ Configuración de apalancamiento y riesgo
# ================================================================
LEVERAGE = int(os.getenv("LEVERAGE", 20))
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", 20))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.05))  # 5% por operación
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", 0.1))  # 10% del capital
ACCOUNT_BALANCE = float(os.getenv("ACCOUNT_BALANCE", 1000))  # Balance estimado (USDT)

# ================================================================
# 💹 Umbrales de ROI (gestión de pérdidas y ganancias)
# ================================================================
ROI_REVERSION_THRESHOLD = float(os.getenv("ROI_REVERSION_THRESHOLD", -30))
ROI_DYNAMIC_STOP_THRESHOLD = float(os.getenv("ROI_DYNAMIC_STOP_THRESHOLD", 60))
ROI_TAKE_PROFIT_THRESHOLD = float(os.getenv("ROI_TAKE_PROFIT_THRESHOLD", 100))
ROI_PARTIAL_CLOSE_PERCENT = float(os.getenv("ROI_PARTIAL_CLOSE_PERCENT", 70))

# ================================================================
# 📊 Configuración de análisis técnico
# ================================================================
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ATR_PERIOD = 14
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Temporalidades por defecto para el análisis
DEFAULT_TIMEFRAMES = ["1", "5", "15"]

# ================================================================
# ⏱️ Intervalos de revisión / monitoreo
# ================================================================
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400

REVIEW_INTERVAL_NORMAL = 900   # 15 minutos
REVIEW_INTERVAL_HIGH_VOL = 300  # 5 minutos
MAX_WAIT_TIME = 24 * SECONDS_IN_HOUR
EXTENDED_MONITORING_TIMEOUT = 72 * SECONDS_IN_HOUR

# ================================================================
# 📈 Condiciones de vigilancia extendida
# ================================================================
EXTENDED_MONITORING_CONDITIONS = {
    "min_atr_multiplier": 1.3,
    "max_price_deviation": 0.15,
    "rsi_extreme_threshold": 25,
    "weekend_extension_hours": 48
}

# ================================================================
# 🔁 Umbrales de reactivación de señales
# ================================================================
REACTIVATION_THRESHOLDS = {
    "confirmation_min_match": 60,
    "price_proximity": 0.08,
    "volatility_increase": 1.2
}

# ================================================================
# 🧪 Validación opcional al iniciar
# ================================================================
def validate_config():
    """Verifica que las variables críticas estén configuradas."""
    missing = []

    if not TELEGRAM_API_ID:
        missing.append("TELEGRAM_API_ID")
    if not TELEGRAM_API_HASH:
        missing.append("TELEGRAM_API_HASH")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_USER_ID:
        missing.append("TELEGRAM_USER_ID")
    if not TELEGRAM_SIGNAL_CHANNEL_ID:
        missing.append("TELEGRAM_SIGNAL_CHANNEL_ID")

    if missing:
        raise ValueError(f"⚠️ Faltan variables críticas en .env: {', '.join(missing)}")

    print(f"✅ Configuración validada correctamente. Entorno: {BYBIT_ENV.upper()}")
    print(f"🌍 Endpoint activo: {BYBIT_ENDPOINT}")

# ================================================================
# 📌 Ejecución directa para validar entorno
# ================================================================
if __name__ == "__main__":
    validate_config()

ANALYSIS_DEBUG_MODE = True  # Cambia a False para producció