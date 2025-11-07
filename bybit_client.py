"""
bybit_client.py
---------------------------------------------------------
Cliente de conexión con la API pública y privada de Bybit.
Incluye:
- get_ohlcv_data(): descarga datos de velas OHLCV
- get_open_positions(): consulta posiciones activas
- open_position(): crea operaciones (simulado o real)
---------------------------------------------------------
Compatible con:
    indicators.py
    signal_manager.py
    operation_tracker.py
---------------------------------------------------------
"""

import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from datetime import datetime
from config import (
    BYBIT_API_KEY,
    BYBIT_API_SECRET,
    BYBIT_CATEGORY,
    SIMULATION_MODE,
    BYBIT_TESTNET,
)

logger = logging.getLogger("bybit_client")

# ================================================================
# 🌐 Base URLs
# ================================================================
BASE_URL_MAINNET = "https://api.bybit.com"
BASE_URL_TESTNET = "https://api-testnet.bybit.com"
BASE_URL = BASE_URL_TESTNET if BYBIT_TESTNET or SIMULATION_MODE else BASE_URL_MAINNET

# ================================================================
# 🕒 Control de tasa de llamadas
# ================================================================
_last_request_time = 0
MIN_REQUEST_INTERVAL = 1.5  # segundos entre llamadas públicas


def _safe_request(method: str, endpoint: str, params=None, headers=None):
    """
    Envuelve las solicitudes HTTP para manejar errores y pausas seguras.
    """
    global _last_request_time
    try:
        elapsed = time.time() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)

        url = BASE_URL + endpoint
        response = requests.request(method, url, params=params, headers=headers, timeout=10)

        _last_request_time = time.time()
        if response.status_code != 200:
            logger.error(f"⚠️ Respuesta inesperada de Bybit ({response.status_code}): {response.text}")
            return None

        data = response.json()
        if data.get("retCode") not in (0, None):
            logger.warning(f"⚠️ Error de API Bybit: {data}")
            return None

        return data

    except Exception as e:
        logger.error(f"❌ Error en solicitud HTTP a Bybit: {e}")
        return None


# ================================================================
# 🔐 Firma para API privada
# ================================================================
def generate_signature(params: dict) -> str:
    """
    Genera una firma HMAC-SHA256 para la API privada.
    """
    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ================================================================
# 📊 Obtener velas OHLCV
# ================================================================
def get_ohlcv_data(symbol: str, timeframe: str = "5m", limit: int = 200) -> pd.DataFrame:
    """
    Obtiene datos OHLCV desde la API pública de Bybit.
    Compatible con pandas_ta.
    Devuelve DataFrame con columnas: time, open, high, low, close, volume.
    """

    # Mapeo de timeframes
    tf_map = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "4h": "240",
        "1d": "D",
    }
    interval = tf_map.get(timeframe, "5")

    endpoint = "/v5/market/kline"
    params = {
        "category": BYBIT_CATEGORY,
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    data = _safe_request("GET", endpoint, params=params)
    if not data or "result" not in data or "list" not in data["result"]:
        logger.warning(f"⚠️ No se pudieron obtener velas para {symbol} ({timeframe})")
        return None

    try:
        records = data["result"]["list"]
        df = pd.DataFrame(records, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"❌ Error procesando OHLCV {symbol} ({timeframe}): {e}")
        return None


# ================================================================
# 📂 Obtener posiciones abiertas
# ================================================================
def get_open_positions() -> list:
    """
    Obtiene posiciones abiertas (reales o simuladas).
    """
    if SIMULATION_MODE:
        logger.info("💬 [SIM] Posiciones simuladas cargadas.")
        return [
            {"symbol": "BTCUSDT", "direction": "long", "entry": 68000.0, "leverage": 20},
            {"symbol": "ETHUSDT", "direction": "short", "entry": 3600.0, "leverage": 20},
        ]

    try:
        endpoint = "/v5/position/list"
        params = {"category": BYBIT_CATEGORY, "settleCoin": "USDT", "limit": 20}
        params["api_key"] = BYBIT_API_KEY
        params["timestamp"] = int(time.time() * 1000)
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


# ================================================================
# 🧾 Crear una operación (simulada o real)
# ================================================================
def open_position(symbol: str, direction: str, amount: float, leverage: int = 20):
    """
    Abre una operación en Bybit (o simulada).
    """
    if SIMULATION_MODE:
        logger.info(f"💬 [SIM] Abrir operación: {symbol} {direction.upper()} x{leverage} ${amount}")
        return {"status": "simulated", "symbol": symbol, "direction": direction}

    try:
        endpoint = "/v5/order/create"
        side = "Buy" if direction == "long" else "Sell"
        params = {
            "api_key": BYBIT_API_KEY,
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": amount,
            "leverage": leverage,
            "timestamp": int(time.time() * 1000),
        }
        params["sign"] = generate_signature(params)

        response = requests.post(BASE_URL + endpoint, params=params, timeout=10)
        data = response.json()

        if data.get("retCode") == 0:
            logger.info(f"✅ Orden abierta: {symbol} {direction.upper()} x{leverage}")
            return {"status": "ok", "data": data}
        else:
            logger.warning(f"⚠️ Orden no ejecutada: {data}")
            return {"status": "failed", "data": data}

    except Exception as e:
        logger.error(f"❌ Error abriendo posición: {e}")
        return {"status": "error", "message": str(e)}


# ================================================================
# 🧪 Test local manual
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_ohlcv_data("BTCUSDT", "5m", limit=100)
    print(df.tail())
