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
