"""
bybit_client_v13_signals_fix.py
--------------------------------
Versión estable 2025 — sincronizada con indicators.py y signal_manager.py.
Optimizada para señales, soporte UTA/Linear, entorno demo o real.
"""

import time
import hmac
import hashlib
import logging
import pandas as pd
import requests
from config import BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_ENDPOINT, BYBIT_ENV, SIMULATION_MODE

logger = logging.getLogger("bybit_client")


# ================================================================
# 🔐 Firma HMAC
# ================================================================
def _sign(params: dict) -> str:
    """Genera firma HMAC-SHA256 (Bybit V5)."""
    query = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


# ================================================================
# 🧭 Detectar entorno (demo o real)
# ================================================================
def detect_env():
    env = BYBIT_ENV.lower().strip()
    if "demo" in env:
        endpoint = "https://api-demo.bybit.com"
    else:
        endpoint = "https://api.bybit.com"
    return env, endpoint


# ================================================================
# 📈 Obtener velas OHLCV
# ================================================================
def get_ohlcv_data(symbol: str, interval: str = "5", limit: int = 200, category: str = "linear"):
    """Obtiene datos OHLCV desde Bybit."""
    try:
        env, endpoint = detect_env()
        url = f"{endpoint}/v5/market/kline"
        params = {"category": category, "symbol": symbol, "interval": interval, "limit": limit}

        r = requests.get(url, params=params, timeout=10)
        data = r.json() if r.text else {}

        if not data or data.get("retCode") != 0:
            # fallback a 'spot' si falla linear/unified
            if category != "spot":
                return get_ohlcv_data(symbol, interval, limit, category="spot")
            logger.warning(f"⚠️ Respuesta inválida de Bybit OHLCV ({symbol}): {data}")
            return None

        candles = data.get("result", {}).get("list", [])
        if not candles:
            return None

        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp")
        logger.info(f"📊 {symbol}: {len(df)} velas {interval}m cargadas correctamente ({category}).")
        return df

    except Exception as e:
        logger.error(f"❌ Error procesando OHLCV para {symbol}: {e}")
        return None


# ================================================================
# 📊 Obtener posiciones abiertas (placeholder seguro)
# ================================================================
def get_open_positions():
    """Devuelve lista vacía (sin error) hasta integración con seguimiento real."""
    logger.warning("⚠️ get_open_positions(): No implementado para UTA demo.")
    return []


# ================================================================
# 🧪 Test rápido
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"🧭 BYBIT_ENV: {BYBIT_ENV}")
    print(f"🌍 BYBIT_ENDPOINT: {BYBIT_ENDPOINT}")
    print(f"💡 SIMULATION_MODE: {SIMULATION_MODE}")
    print("🚀 Test Bybit v13 — autodetección de categorías (señales fix)\n")

    for pair in ["BTCUSDT", "ZECUSDT", "PROMPTUSDT", "UBUSDT"]:
        print(f"\n📊 Probando {pair}...")
        df = get_ohlcv_data(pair, "5")
        if df is not None:
            print(df.tail(2))

    print("\n📡 Buscando posiciones abiertas...\n")
    positions = get_open_positions()
    print("Resultado:", positions)
