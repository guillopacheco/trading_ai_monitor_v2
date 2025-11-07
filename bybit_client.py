import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from config import BYBIT_API_KEY, BYBIT_API_SECRET, SIMULATION_MODE, BYBIT_TESTNET

logger = logging.getLogger("bybit_client")

BASE_URL = "https://api-testnet.bybit.com" if BYBIT_TESTNET else "https://api.bybit.com"


# ================================================================
# 🔐 Firma segura HMAC-SHA256
# ================================================================
def generate_signature(params: dict) -> str:
    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ================================================================
# 📈 Obtener OHLCV (segura, dinámica)
# ================================================================
def get_ohlcv_data(symbol: str, interval="1m", limit=200):
    """
    Devuelve un DataFrame con columnas: timestamp, open, high, low, close, volume
    Compatible con Testnet o producción.
    """
    try:
        endpoint = "/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        response = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        data = response.json()

        if "result" not in data or "list" not in data["result"]:
            logger.warning(f"⚠️  Sin datos OHLCV para {symbol} ({interval})")
            return None

        raw_data = data["result"]["list"]
        if not raw_data:
            return None

        # Bybit devuelve a veces 7 columnas → adaptamos dinámicamente
        df = pd.DataFrame(raw_data)
        df.columns = df.columns[:7]  # prevenir error de longitud
        df = df.iloc[:, :6]  # mantener solo las 6 columnas principales
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]

        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms")
        df = df.astype(float, errors="ignore")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"❌ Error procesando OHLCV {symbol} ({interval}): {e}")
        return None


# ================================================================
# 📊 Posiciones abiertas
# ================================================================
def get_open_positions():
    if SIMULATION_MODE:
        logger.info("💬 [SIM] Posiciones simuladas cargadas.")
        return [
            {"symbol": "BTCUSDT", "direction": "long", "entry": 68000.0, "leverage": 20},
            {"symbol": "ETHUSDT", "direction": "short", "entry": 3600.0, "leverage": 20},
        ]

    try:
        endpoint = "/v5/position/list"
        params = {
            "category": "linear",
            "settleCoin": "USDT",
            "limit": 20,
            "api_key": BYBIT_API_KEY,
            "timestamp": int(time.time() * 1000),
        }
        params["sign"] = generate_signature(params)
        response = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        data = response.json()

        positions = []
        if "result" in data and "list" in data["result"]:
            for pos in data["result"]["list"]:
                if float(pos.get("size", 0)) > 0:
                    positions.append({
                        "symbol": pos["symbol"],
                        "direction": "long" if pos["side"] == "Buy" else "short",
                        "entry": float(pos["avgPrice"]),
                        "leverage": int(pos["leverage"]),
                    })
        logger.info(f"📊 {len(positions)} posiciones activas detectadas")
        return positions

    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones abiertas: {e}")
        return []
