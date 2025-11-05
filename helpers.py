import logging
import requests
from config import SIMULATION_MODE

logger = logging.getLogger("helpers")


# ================================================================
# 🔧 Normalización de símbolo
# ================================================================
def normalize_symbol(raw_symbol: str) -> str:
    """Convierte un símbolo del formato '#BTC/USDT' a 'BTCUSDT'."""
    try:
        normalized = raw_symbol.replace("#", "").replace("/", "").upper()
        logger.debug(f"🔧 Normalizando símbolo: {raw_symbol} -> {normalized}")
        return normalized
    except Exception as e:
        logger.error(f"❌ Error normalizando símbolo {raw_symbol}: {e}")
        return raw_symbol


# ================================================================
# 💰 Cálculo ROI con apalancamiento
# ================================================================
def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int = 20) -> float:
    """
    Calcula el ROI (%) de una operación teniendo en cuenta el apalancamiento y la dirección.
    """
    try:
        if direction.lower() == "long":
            roi = ((current_price - entry_price) / entry_price) * leverage * 100
        else:
            roi = ((entry_price - current_price) / entry_price) * leverage * 100
        return round(roi, 2)
    except Exception as e:
        logger.error(f"❌ Error calculando ROI: {e}")
        return 0.0


# ================================================================
# 📈 Precio actual (simulación o real)
# ================================================================
def get_current_price(symbol: str) -> float:
    """
    Obtiene el precio actual del par desde Bybit (modo real) o genera valor simulado.
    """
    try:
        if SIMULATION_MODE:
            import random
            simulated = round(random.uniform(0.98, 1.02), 4)
            logger.info(f"💬 [SIM] Precio simulado {symbol}: {simulated}")
            return simulated

        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        response = requests.get(url, timeout=5)
        data = response.json()

        if "result" in data and "list" in data["result"]:
            price = float(data["result"]["list"][0]["lastPrice"])
            logger.info(f"💵 Precio actual {symbol}: {price}")
            return price
        else:
            logger.warning(f"⚠️ No se encontró precio válido para {symbol}")
            return 0.0

    except Exception as e:
        logger.error(f"❌ Error obteniendo precio de {symbol}: {e}")
        return 0.0


# ================================================================
# 📊 Cálculo de coincidencia técnica (match ratio)
# ================================================================
def calculate_match_ratio(trend_summary: dict, direction: str) -> float:
    """
    Calcula qué porcentaje de temporalidades coincide con la dirección de la señal.
    """
    try:
        matches = sum(1 for trend in trend_summary.values() if trend == direction)
        ratio = matches / len(trend_summary) if trend_summary else 0
        logger.debug(f"📊 Match ratio {direction.upper()}: {ratio:.2f}")
        return round(ratio, 2)
    except Exception as e:
        logger.error(f"❌ Error calculando match ratio: {e}")
        return 0.0
