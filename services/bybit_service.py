"""
services/bybit_service.py
-------------------------
Cliente UNIFICADO Bybit (API v5)
✔ Funciona con claves privadas
✔ Permite leer posiciones reales
✔ Obtiene OHLCV
✔ Obtiene balances
✔ Obtiene órdenes
"""

import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from urllib.parse import urlencode

from config import (
    BYBIT_API_KEY,
    BYBIT_API_SECRET,
    BYBIT_ENDPOINT,
    BYBIT_CATEGORY,
)

logger = logging.getLogger("bybit_service")


# ============================================================
# 🔐 Firma para API Bybit v5
# ============================================================

def _sign(params: dict) -> str:
    """
    Firma HMAC-SHA256 requerida por Bybit v5
    """
    qs = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    sig = hmac.new(
        BYBIT_API_SECRET.encode(),
        qs.encode(),
        hashlib.sha256
    ).hexdigest()
    return sig


def _private_get(endpoint: str, params: dict) -> dict:
    """
    Request GET firmada para API privada de Bybit v5
    """
    ts = str(int(time.time() * 1000))

    base = {
        "api_key": BYBIT_API_KEY,
        "timestamp": ts,
        "recvWindow": "5000",
    }

    full = {**base, **params}
    signature = _sign(full)
    full["sign"] = signature

    url = f"{BYBIT_ENDPOINT}/v5/{endpoint}?{urlencode(full)}"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return data
    except Exception as e:
        logger.error(f"❌ Error en API privada {endpoint}: {e}")
        return {"retCode": -1, "retMsg": str(e), "result": {}}


# ============================================================
# 📊 OHLCV público
# ============================================================

def get_ohlcv(symbol: str, interval: str = "60", limit: int = 200):
    """
    Velas OHLCV de Bybit (API pública)
    """
    url = f"{BYBIT_ENDPOINT}/v5/market/kline"
    params = {
        "category": BYBIT_CATEGORY,
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data.get("retCode") != 0:
            logger.warning(f"⚠️ OHLCV error {symbol}: {data}")
            return None

        rows = data["result"].get("list", [])
        if not rows:
            return None

        df = pd.DataFrame(
            rows,
            columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = df[c].astype(float)

        return df.sort_values("timestamp")

    except Exception as e:
        logger.error(f"❌ Error OHLCV {symbol}: {e}")
        return None


# ============================================================
# 💼 Balance de cuenta
# ============================================================

def get_account_balance():
    """
    Devuelve balances de cuenta USDT
    """
    data = _private_get("account/wallet-balance", {"accountType": "UNIFIED"})

    if data.get("retCode") != 0:
        return {"error": data.get("retMsg")}

    return data["result"]["list"][0]


# ============================================================
# 📈 POSICIONES ABIERTAS
# ============================================================

def get_open_positions():
    """
    Obtiene posiciones abiertas reales.
    Devuelve lista limpia compatible con positions_controller.
    """

    params = {
        "category": "linear",
        "settleCoin": "USDT",
    }

    data = _private_get("position/list", params)

    if data.get("retCode") != 0:
        logger.error(f"❌ Error posiciones: {data}")
        return []

    positions = data.get("result", {}).get("list", [])

    cleaned = []
    for p in positions:
        size = float(p.get("size", 0))
        if size <= 0:
            continue

        # fallback cuando entryPrice viene vacío
        entry = p.get("entryPrice")
        if not entry or entry == "0":
            avg = p.get("avgPrice")
            if avg and float(avg) > 0:
                p["entryPrice"] = avg

        cleaned.append(p)

    return cleaned


# ============================================================
# 🔵 ÓRDENES ABIERTAS
# ============================================================

def get_open_orders():
    """
    Devuelve órdenes abiertas en Bybit.
    """
    params = {
        "category": "linear",
        "settleCoin": "USDT",
        "openOnly": "1",
    }

    data = _private_get("order/realtime", params)
    if data.get("retCode") != 0:
        return []

    return data.get("result", {}).get("list", [])


# ============================================================
# 🔵 Precio actual del símbolo
# ============================================================

def get_symbol_price(symbol: str):
    url = f"{BYBIT_ENDPOINT}/v5/market/tickers"
    params = {"category": BYBIT_CATEGORY, "symbol": symbol.upper()}

    try:
        r = requests.get(url, params=params, timeout=8)
        data = r.json()

        if data.get("retCode") != 0:
            return None

        items = data["result"].get("list", [])
        if not items:
            return None

        return float(items[0]["lastPrice"])

    except Exception as e:
        logger.error(f"❌ Error precio {symbol}: {e}")
        return None
