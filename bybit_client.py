import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from config import BYBIT_API_KEY, BYBIT_API_SECRET, SIMULATION_MODE, BYBIT_TESTNET

logger = logging.getLogger("bybit_client")

# ================================================================
# 🌐 Endpoint dinámico
# ================================================================
BYBIT_ENDPOINT = (
    "https://api-testnet.bybit.com"
    if BYBIT_TESTNET and not SIMULATION_MODE
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
# 📈 Obtener OHLCV (robusta con fallback y latencia)
# ================================================================
def get_ohlcv_data(symbol: str, interval: str = "5", limit: int = 500):
    """
    Recupera datos OHLCV de Bybit Futuros (Linear) con manejo de intervalos,
    reintentos, validación de estructura y logs de latencia.
    """
    valid_intervals = {"1", "3", "5", "15", "30", "60", "240", "D"}
    if interval not in valid_intervals:
        logger.warning(f"⚠️ Intervalo no válido '{interval}', usando '5'")
        interval = "5"

    url = f"{BYBIT_ENDPOINT}/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    for attempt in range(3):
        try:
            start_time = time.time()
            r = requests.get(url, params=params, timeout=10)
            latency = time.time() - start_time

            if r.status_code != 200:
                logger.error(f"❌ HTTP {r.status_code} ({latency:.2f}s) — {r.text}")
                time.sleep(2)
                continue

            data = r.json()
            if data.get("retCode") != 0 or not data.get("result"):
                logger.warning(f"⚠️ Respuesta inválida ({latency:.2f}s): {data}")
                time.sleep(2)
                continue

            rows = data["result"].get("list", [])
            if not rows or len(rows) < 50:
                logger.warning(f"⚠️ Insuficientes velas ({len(rows)}) para {symbol} ({interval}m)")
                if attempt == 2 and interval != "1":
                    logger.info(f"🔁 Reintentando con temporalidad menor (1m)")
                    return get_ohlcv_data(symbol, "1", limit)
                time.sleep(2)
                continue

            # Crear DataFrame robusto
            df = pd.DataFrame(rows)
            if df.shape[1] >= 6:
                df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"][:df.shape[1]]
            else:
                logger.error(f"❌ Estructura inesperada: {df.shape}")
                return None

            df = df.astype({
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float
            })
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            df = df.sort_values("timestamp")

            logger.info(f"📊 {symbol}: {len(df)} velas {interval}m cargadas en {latency:.2f}s.")
            return df

        except Exception as e:
            logger.error(f"❌ Intento {attempt+1}: {e}")
            time.sleep(2)

    logger.error(f"❌ No se pudo obtener OHLCV para {symbol} tras 3 intentos.")
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
        response = requests.get(BYBIT_ENDPOINT + endpoint, params=params, timeout=10)
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

        logger.info(f"📊 {len(positions)} posiciones activas detectadas.")
        return positions

    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones abiertas: {e}")
        return []
