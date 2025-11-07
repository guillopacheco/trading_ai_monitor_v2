"""
Funciones auxiliares para cálculos de riesgo, ROI y operaciones
"""
import logging
import random
import re

logger = logging.getLogger("helpers")

# ================================================================
# ⚙️ Configuración de apalancamiento y riesgo
# ================================================================
LEVERAGE = 20
RISK_PER_TRADE = 0.05
MAX_LEVERAGE = 20
MAX_POSITION_SIZE = 0.1
ACCOUNT_BALANCE = 1000

# ================================================================
# 💹 Umbrales ROI (gestión de pérdidas y ganancias)
# ================================================================
ROI_REVERSION_THRESHOLD = -30
ROI_DYNAMIC_STOP_THRESHOLD = 60
ROI_TAKE_PROFIT_THRESHOLD = 100
ROI_PARTIAL_CLOSE_PERCENT = 70

# ================================================================
# 🔤 Normalización de símbolos
# ================================================================
def normalize_symbol(raw_symbol: str) -> str:
    """
    Limpia y estandariza el nombre del símbolo para uso en Bybit.
    Ejemplos:
      "#BTC/USDT" -> "BTCUSDT"
      "ethusdt"   -> "ETHUSDT"
      "SOL"       -> "SOLUSDT"
    """
    try:
        # Quitar caracteres no alfabéticos ni numéricos relevantes
        symbol = re.sub(r"[^A-Za-z0-9/]", "", raw_symbol).upper()

        # Si ya incluye /USDT → reemplazar por USDT
        if symbol.endswith("/USDT"):
            symbol = symbol.replace("/", "")
        elif not symbol.endswith("USDT"):
            symbol = symbol + "USDT"

        logger.debug(f"🔤 Normalizado símbolo: {raw_symbol} -> {symbol}")
        return symbol
    except Exception as e:
        logger.error(f"❌ Error normalizando símbolo {raw_symbol}: {e}")
        return raw_symbol.upper()

# ================================================================
# 💰 Cálculos de ROI y precio actual
# ================================================================
def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int) -> float:
    try:
        pnl = ((current_price - entry_price) / entry_price) * 100
        if direction.lower() == "short":
            pnl *= -1
        roi = pnl * leverage
        return round(roi, 2)
    except Exception as e:
        logger.error(f"Error calculando ROI: {e}")
        return 0.0

def get_current_price(symbol: str) -> float:
    # ⚠️ Este valor se obtiene de Bybit o se simula según el modo
    try:
        # En modo simulación, retorna un valor aleatorio entre ±2%
        return round(random.uniform(0.98, 1.02), 4)
    except Exception as e:
        logger.error(f"Error obteniendo precio actual para {symbol}: {e}")
        return 0.0
