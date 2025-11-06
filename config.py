# ================================================================
# 📦 CONFIGURACIÓN GLOBAL DEL SISTEMA
# ================================================================
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ================================================================
# 🤖 TELEGRAM - CUENTA PERSONAL Y BOT
# ================================================================
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION", "trading_ai_monitor")
TELEGRAM_SIGNAL_CHANNEL_ID = os.getenv("TELEGRAM_SIGNAL_CHANNEL_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")

# ================================================================
# 💹 BYBIT - API KEYS Y ENDPOINTS
# ================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# Usa testnet si la variable existe y es True
BYBIT_TESTNET = os.getenv("BYBIT_TESTNET", "False").lower() == "true"

# Selección del endpoint
BYBIT_BASE_URL = (
    "https://api-testnet.bybit.com" if BYBIT_TESTNET else "https://api.bybit.com"
)

# ================================================================
# ⚙️ MODO DE EJECUCIÓN Y SISTEMA
# ================================================================
# Si True, la app no enviará órdenes reales ni mensajes de Telegram reales
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "True").lower() == "true"

# ================================================================
# 🗄️ BASE DE DATOS LOCAL
# ================================================================
DATABASE_FILE = os.getenv("DATABASE_FILE", "trading_ai_monitor.db")

# ================================================================
# 🧭 CONFIGURACIONES ADICIONALES (TIEMPOS Y RETRASOS)
# ================================================================
# Intervalo de revisión del sistema (heartbeat)
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "300"))  # segundos

# Tiempo de espera entre llamadas a Bybit API
BYBIT_API_DELAY = float(os.getenv("BYBIT_API_DELAY", "1.5"))

# ================================================================
# 🧠 VALIDACIÓN BÁSICA DE VARIABLES CLAVE
# ================================================================
def validate_env():
    """Verifica que existan las variables esenciales antes de iniciar el sistema."""
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
        print(f"⚠️  Advertencia: faltan variables en .env: {', '.join(missing)}")


# Llamar validación al importar
validate_env()
