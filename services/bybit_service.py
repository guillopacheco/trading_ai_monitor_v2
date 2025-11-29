"""
services/bybit_service.py
-------------------------
Cliente centralizado para la API pública de Bybit (REST v5).

✔ OHLCV para indicadores
✔ Precio actual

La API privada (posiciones reales, órdenes) se puede integrar después.
"""

import logging
from typing import Optional, List, Dict

import requests
import pandas as pd

from config import BYBIT_ENDPOINT, BYBIT_CATEGORY

logger = logging.getLogger("bybit_service")


# ============================================================
# 🔵 OHLCV (velas)
# ============================================================

def get_ohlcv(
    symbol: str,
    interval: str = "60",
    limit: int = 200,
) -> Optional[pd.DataFrame]:
    """
    Devuelve OHLCV como DataFrame ordenado por tiempo ascendente.

    interval (Bybit):
        "1"   = 1m
        "3"   = 3m
        "5"   = 5m
        "15"  = 15m
        "30"  = 30m
        "60"  = 1h
        "240" = 4h
        "D"   = 1D
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
            logger.warning(f"⚠️ Bybit error OHLCV {symbol} ({interval}): {data}")
            return None

        rows = data["result"].get("list", [])
        if not rows:
            logger.warning(f"⚠️ Bybit devolvió lista vacía para {symbol} ({interval})")
            return None

        df = pd.DataFrame(
            rows,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnover",
            ],
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    except Exception as e:
        logger.error(f"❌ Error obteniendo OHLCV de {symbol} ({interval}): {e}")
        return None


# ============================================================
# 🔵 Precio actual
# ============================================================

def get_symbol_price(symbol: str) -> Optional[float]:
    """
    Devuelve el último precio del símbolo (lastPrice).
    """
    url = f"{BYBIT_ENDPOINT}/v5/market/tickers"
    params = {
        "category": BYBIT_CATEGORY,
        "symbol": symbol.upper(),
    }

    try:
        r = requests.get(url, params=params, timeout=8)
        data = r.json()

        if data.get("retCode") != 0:
            logger.warning(f"⚠️ Bybit error tickers {symbol}: {data}")
            return None

        items = data["result"].get("list", [])
        if not items:
            return None

        price = float(items[0]["lastPrice"])
        return price

    except Exception as e:
        logger.error(f"❌ Error obteniendo precio de {symbol}: {e}")
        return None


# ============================================================
# 🔵 Posiciones abiertas (placeholder)
# ============================================================

def get_open_positions() -> List[Dict]:
    """
    Placeholder para integrarse con la API privada de Bybit.

    Actualmente devuelve lista vacía para NO romper el flujo.

    En el futuro:
        - integrar /v5/position/list con API key/secret.
    """
    return []
