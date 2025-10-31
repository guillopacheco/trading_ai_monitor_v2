"""
Configuración centralizada de la aplicación
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Constantes para mejor legibilidad
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400

# Telegram Configuration (Usuario)
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Channels Configuration
SIGNALS_CHANNEL_ID = os.getenv('SIGNALS_CHANNEL_ID')
OUTPUT_CHANNEL_ID = os.getenv('OUTPUT_CHANNEL_ID')

# Bybit Configuration
BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
BYBIT_CATEGORY = "linear"  # ← AÑADE ESTA LÍNEA

# Trading Configuration
APP_MODE = os.getenv('APP_MODE', 'ANALYSIS')  # ANALYSIS o TRADING
DEFAULT_TIMEFRAMES = ["1", "5", "15"]
REVIEW_INTERVAL_NORMAL = 900  # 15 minutos
REVIEW_INTERVAL_HIGH_VOL = 300  # 5 minutos
MAX_WAIT_TIME = 24 * SECONDS_IN_HOUR  # 24 horas
EXTENDED_MONITORING_TIMEOUT = 72 * SECONDS_IN_HOUR  # 72 horas

# Configuración de Apalancamiento y Riesgo
LEVERAGE = 20
RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', 0.02))  # 2% por operación
MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', 20))  # CAMBIADO a 20
MAX_POSITION_SIZE = 0.1  # 10% máximo del capital por operación
ACCOUNT_BALANCE = 1000  # Balance de cuenta estimado en USDT
# App Settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Ajustar stops para apalancamiento
BASE_STOP_PERCENTAGE = 0.03
MIN_STOP_DISTANCE = 0.005
MAX_STOP_DISTANCE = 0.08

# Condiciones para vigilancia extendida
EXTENDED_MONITORING_CONDITIONS = {
    'min_atr_multiplier': 1.3,
    'max_price_deviation': 0.15,
    'rsi_extreme_threshold': 25,
    'weekend_extension_hours': 48
}

# Umbrales para re-activación de señales
REACTIVATION_THRESHOLDS = {
    'confirmation_min_match': 60,
    'price_proximity': 0.08,
    'volatility_increase': 1.2
}

# Indicadores Configuration
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ATR_PERIOD = 14
EMA_SHORT_PERIOD = 10
EMA_LONG_PERIOD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Database
DATABASE_PATH = "data/trading_signals.db"

# ROI Management (NUEVO - para el prompt original)
ROI_REVERSION_THRESHOLD = -30  # -30% para considerar reversión
ROI_DYNAMIC_STOP_THRESHOLD = 60  # +60% para SL dinámico
ROI_TAKE_PROFIT_THRESHOLD = 100  # +100% para TP parcial
ROI_PARTIAL_CLOSE_PERCENT = 70  # 70% de la posición

def validate_config():
    """Valida que la configuración esencial esté presente"""
    errors = []
    
    # Verificar configuración de User Bot
    if not TELEGRAM_API_ID:
        errors.append("TELEGRAM_API_ID no configurado")
    if not TELEGRAM_API_HASH:
        errors.append("TELEGRAM_API_HASH no configurado")
    if not TELEGRAM_PHONE:
        errors.append("TELEGRAM_PHONE no configurado")
    
    # Verificar Bot Token
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN no configurado")
    
    # Verificar canales
    if not SIGNALS_CHANNEL_ID:
        errors.append("SIGNALS_CHANNEL_ID no configurado")
    if not OUTPUT_CHANNEL_ID:
        errors.append("OUTPUT_CHANNEL_ID no configurado")
    
    if errors:
        error_msg = "Errores de configuración:\n- " + "\n- ".join(errors)
        raise ValueError(error_msg)
    
    print("✅ Configuración validada correctamente")

if __name__ == "__main__":
    validate_config()