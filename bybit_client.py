import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from config import BYBIT_API_KEY, BYBIT_API_SECRET, SIMULATION_MODE, BYBIT_TESTNET

logger = logging.getLogger("bybit_client")

# ================================================================
# 🌐 Endpoint según entorno
# ================================================================
BYBIT_ENDPOINT = (
    "https://api-testnet.bybit.com"
    if (SIMULATION_MODE or str(BYBIT_TESTNET).lower() == "true")
    else "https://api.bybit.com"
)

# ================================================================
# 🔐 Firma HMAC-SHA256
# ================================================================
def generate_signature(params: dict) -> str:
    """Genera firma HMAC SHA256 para Bybit."""
    query = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

# ================================================================
# 📈 Obtener datos OHLCV
# ================================================================
def get_ohlcv_data(symbol: str, interval: str = "5", limit: int = 500):
    """Obtiene datos OHLCV de Bybit para contratos perpetuos (UTA)."""
    try:
        url = f"{BYBIT_ENDPOINT}/v5/market/kline"
        params = {
            "category": "linear",  # Futures perpetuos USDT
            "contractType": "PERPETUAL",  # Requerido en cuentas UTA
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }

        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            logger.error(f"❌ Error HTTP {r.status_code}: {r.text}")
            return None

        data = r.json()
        if data.get("retCode") != 0:
            logger.warning(f"⚠️ Error de Bybit OHLCV: {data}")
            return None

        rows = data["result"].get("list", [])
        if not rows:
            logger.warning(f"⚠️ No hay velas para {symbol}")
            return None

        df = pd.DataFrame(rows)
        df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df = df.astype({
            "open": float, "high": float, "low": float,
            "close": float, "volume": float,
        })
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        df = df.sort_values("timestamp")
        logger.info(f"📊 {symbol}: {len(df)} velas {interval}m cargadas correctamente.")
        return df

    except Exception as e:
        logger.error(f"❌ Error en get_ohlcv_data({symbol}): {e}")
        return None

# ================================================================
# 📊 Obtener posiciones abiertas
# ================================================================
def get_open_positions():
    """Obtiene las posiciones abiertas (UTA o simulación)."""
    if SIMULATION_MODE:
        logger.info("💬 [SIM] Posiciones simuladas cargadas.")
        return [
            {"symbol": "BTCUSDT", "direction": "long", "entry": 68000.0, "leverage": 20},
            {"symbol": "ETHUSDT", "direction": "short", "entry": 3600.0, "leverage": 20},
        ]

    try:
        url = f"{BYBIT_ENDPOINT}/v5/position/list"
        body = {
            "category": "linear",
            "settleCoin": "USDT",
            "contractType": "PERPETUAL",  # Necesario para UTA
            "api_key": BYBIT_API_KEY,
            "timestamp": int(time.time() * 1000),
            "recv_window": 5000,
        }

        sign_payload = "&".join(f"{k}={body[k]}" for k in sorted(body))
        body["sign"] = generate_signature(body)

        r = requests.post(url, data=body, timeout=10)
        if not r.text.strip():
            logger.error("❌ Respuesta vacía de Bybit al solicitar posiciones.")
            return []

        data = r.json()
        if data.get("retCode") != 0:
            logger.error(f"❌ Error API Bybit: {data}")
            return []

        positions = []
        for pos in data["result"].get("list", []):
            if float(pos.get("size", 0)) > 0:
                positions.append({
                    "symbol": pos["symbol"],
                    "direction": "long" if pos["side"] == "Buy" else "short",
                    "entry": float(pos["avgPrice"]),
                    "leverage": int(float(pos.get("leverage", 20))),
                })

        logger.info(f"📊 {len(positions)} posiciones activas detectadas.")
        return positions

    except Exception as e:
        logger.error(f"❌ Error en get_open_positions(): {e}")
        return []

# ================================================================
# 🧪 Test local
# ================================================================
if __name__ == "__main__":
    print("🚀 Test rápido del cliente Bybit (UTA Real)")
    df = get_ohlcv_data("PROMPTUSDT", "5")
    if df is not None:
        print(df.tail(3))
    print("Posiciones abiertas:", get_open_positions())
