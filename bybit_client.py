import time
import hmac
import hashlib
import requests
import logging

from config import BYBIT_API_KEY, BYBIT_API_SECRET, SIMULATION_MODE

# Opcionales/seguro por defecto si no existen en config.py
try:
    from config import BYBIT_TESTNET, BYBIT_CATEGORY
except Exception:
    BYBIT_TESTNET = False
    BYBIT_CATEGORY = "linear"  # "linear", "inverse" o "spot"

logger = logging.getLogger("bybit_client")

BASE_URL = "https://api.bybit.com" if not BYBIT_TESTNET else "https://api-testnet.bybit.com"

# Mapa timeframe → intervalo v5
INTERVAL_MAP = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "1w": "W",
    "1M": "M",
}

# ================================================================
# 🔐 Generación de firma segura (para endpoints privados)
# ================================================================
def generate_signature(params: dict) -> str:
    """Genera una firma HMAC-SHA256 para la API privada."""
    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ================================================================
# 📊 OHLCV (velas) — endpoint público v5
# ================================================================
def get_ohlcv(symbol: str, timeframe: str, limit: int = 200, category: str = None):
    """
    Devuelve lista de dicts OHLCV usando /v5/market/kline
    Formato:
    [
      {'timestamp': int_ms, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': float},
      ...
    ]
    """
    try:
        interval = INTERVAL_MAP.get(timeframe)
        if not interval:
            raise ValueError(f"Timeframe no soportado: {timeframe}")

        endpoint = "/v5/market/kline"
        params = {
            "category": category or BYBIT_CATEGORY or "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": min(max(int(limit), 1), 1000),
        }
        resp = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        data = resp.json()

        if data.get("retCode") != 0 or "result" not in data or "list" not in data["result"]:
            logger.warning(f"⚠️ Respuesta kline inesperada: {data}")
            return []

        rows = []
        # Bybit v5 kline list: [startTime, open, high, low, close, volume, turnover]
        for it in data["result"]["list"]:
            ts = int(it[0])
            o, h, l, c, vol = float(it[1]), float(it[2]), float(it[3]), float(it[4]), float(it[5])
            rows.append({
                "timestamp": ts,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": vol
            })
        return rows

    except Exception as e:
        logger.error(f"❌ Error get_ohlcv {symbol} {timeframe}: {e}")
        return []


# ================================================================
# 📂 Posiciones abiertas (privado)
# ================================================================
def get_open_positions() -> list:
    """
    Obtiene las posiciones abiertas desde la API privada de Bybit.
    En modo simulación devuelve posiciones falsas para pruebas.
    """
    if SIMULATION_MODE:
        logger.info("💬 [SIM] Posiciones simuladas cargadas.")
        return [
            {"symbol": "BTCUSDT", "direction": "long", "entry": 68000.0, "leverage": 20},
            {"symbol": "ETHUSDT", "direction": "short", "entry": 3600.0, "leverage": 20},
        ]

    try:
        endpoint = "/v5/position/list"
        params = {"category": BYBIT_CATEGORY or "linear", "settleCoin": "USDT", "limit": 20}
        params["api_key"] = BYBIT_API_KEY
        params["timestamp"] = int(time.time() * 1000)
        params["sign"] = generate_signature(params)

        response = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        data = response.json()

        positions = []
        if "result" in data and "list" in data["result"]:
            for pos in data["result"]["list"]:
                # Filtra solo posiciones con tamaño > 0
                try:
                    if float(pos.get("size", 0)) > 0:
                        positions.append({
                            "symbol": pos["symbol"],
                            "direction": "long" if pos.get("side") == "Buy" else "short",
                            "entry": float(pos.get("avgPrice", 0)),
                            "leverage": int(float(pos.get("leverage", 20))),
                        })
                except Exception:
                    continue

        logger.info(f"📊 {len(positions)} posiciones activas detectadas")
        return positions

    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones abiertas: {e}")
        return []


# ================================================================
# 🧾 Abrir una operación (opcional futuro)
# ================================================================
def open_position(symbol: str, direction: str, amount: float, leverage: int = 20):
    """
    Abre una posición real o simulada (futuro desarrollo automatizado).
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
