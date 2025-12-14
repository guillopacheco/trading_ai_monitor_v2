# config.py
import os
from dotenv import load_dotenv

load_dotenv()


def _get(name, default=None, cast=str):
    v = os.getenv(name, default)
    if v is None:
        return None
    try:
        return cast(v)
    except Exception:
        return v


# --- Telegram Bot (PTB)
BOT_TOKEN = _get("BOT_TOKEN")
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", BOT_TOKEN)

# Chat destino donde notifica tu bot
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID", None, int)

# --- Telethon (lector de canal)
API_ID = _get("API_ID", _get("TELEGRAM_API_ID"), int)
API_HASH = _get("API_HASH", _get("TELEGRAM_API_HASH"))
TELEGRAM_SESSION = _get("TELEGRAM_SESSION", "session")

# Canal origen (ID numérico -100....)
TELEGRAM_CHANNEL_ID = _get("TELEGRAM_CHANNEL_ID", None, int)

# --- Bybit
BYBIT_API_KEY = _get("BYBIT_API_KEY")
BYBIT_API_SECRET = _get("BYBIT_API_SECRET")
BYBIT_TESTNET = _get("BYBIT_TESTNET", "false").lower() == "true"
BYBIT_SETTLE_COIN = _get("BYBIT_SETTLE_COIN", "USDT")

# Compat extra (por si otros módulos importan estos nombres)
TELEGRAM_API_ID = API_ID
TELEGRAM_API_HASH = API_HASH

# ============================================================
# 🔧 Technical Engine Defaults (para motor_wrapper_core)
# ============================================================

# EMA configuration
EMA_SHORT_PERIOD = int(os.getenv("EMA_SHORT_PERIOD", 10))
EMA_MID_PERIOD = int(os.getenv("EMA_MID_PERIOD", 30))
EMA_LONG_PERIOD = int(os.getenv("EMA_LONG_PERIOD", 50))

# RSI
RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", 70))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", 30))

# MACD
MACD_FAST = int(os.getenv("MACD_FAST", 12))
MACD_SLOW = int(os.getenv("MACD_SLOW", 26))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", 9))

# ATR
ATR_PERIOD = int(os.getenv("ATR_PERIOD", 14))
ATR_HIGH_VOL_THRESHOLD = float(os.getenv("ATR_HIGH_VOL_THRESHOLD", 0.03))

# Timeframes defaults (motor fallback)
DEFAULT_TIMEFRAMES = os.getenv("DEFAULT_TIMEFRAMES", "240,60,30,15").split(",")

DEFAULT_TIMEFRAMES = [tf.strip() for tf in DEFAULT_TIMEFRAMES]

# ============================================================
# 🧠 Analysis / Engine Modes
# ============================================================

# analysis | reactivation | open_position
ANALYSIS_MODE = os.getenv("ANALYSIS_MODE", "analysis")

# strict = no fallback
# safe   = allow fallbacks
ENGINE_MODE = os.getenv("ENGINE_MODE", "safe")
