import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from config import BYBIT_API_KEY, BYBIT_API_SECRET, SIMULATION_MODE, BYBIT_TESTNET


logger = logging.getLogger("bybit_client")

# Detect endpoint dinámico
BYBIT_ENDPOINT = (
    "https://api-testnet.bybit.com"
    if BYBIT_TESTNET or SIMULATION_MODE
    else "https://api.bybit.com"
)

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
def get_ohlcv_data(symbol: str, interval: str = "5", limit: int = 500):
    """
    Recupera datos OHLCV de Bybit Spot o Futuros (Linear).
    Maneja correctamente 6 o 7 columnas y faltantes.
    """
    try:
        url = f"{BYBIT_ENDPOINT}/v5/market/kline"
        params = {
            "category": "linear",  # Para Futuros USDT
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            logger.error(f"❌ Error HTTP {r.status_code} al obtener OHLCV: {r.text}")
            return None

        data = r.json()
        if data.get("retCode") != 0 or not data.get("result"):
            logger.warning(f"⚠️ Sin datos OHLCV válidos para {symbol}: {data}")
            return None

        rows = data["result"].get("list", [])
        if not rows or len(rows) < 50:
            logger.warning(f"⚠️ Insuficientes velas para {symbol} ({interval}m)")
            return None

        # Crear DataFrame tolerante a número variable de columnas
        df = pd.DataFrame(rows)
        # A veces la API devuelve [timestamp, open, high, low, close, volume, turnover]
        if df.shape[1] >= 6:
            df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"][:df.shape[1]]
        else:
            logger.error(f"❌ Estructura inesperada de OHLCV ({df.shape})")
            return None

        # Convertir tipos numéricos
        df = df.astype({
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float
        })

        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        df = df.sort_values("timestamp")

        logger.info(f"📊 {symbol}: {len(df)} velas {interval}m cargadas desde Bybit.")
        return df

    except Exception as e:
        logger.error(f"❌ Error procesando OHLCV {symbol} ({interval}m): {e}")
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
