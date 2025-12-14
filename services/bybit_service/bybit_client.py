import os
import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from urllib.parse import urlencode
import ccxt
from config import BYBIT_SETTLE_COIN

# Instancia CCXT (ajusta si ya la tienes global)
exchange = ccxt.bybit({"enableRateLimit": True, "options": {"defaultType": "linear"}})

logger = logging.getLogger("bybit_client")

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BASE_URL = "https://api.bybit.com"


# ======================================================
# 🔐 AUTH – GENERADOR DE FIRMA
# ======================================================
def _sign(params: dict) -> dict:
    """Genera firma v5 para Bybit."""
    timestamp = str(int(time.time() * 1000))
    params["api_key"] = BYBIT_API_KEY
    params["timestamp"] = timestamp
    query_string = urlencode(sorted(params.items()))
    signature = hmac.new(
        BYBIT_API_SECRET.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    params["sign"] = signature
    return params


# ======================================================
# 🧾 UTILIDAD — PETICIÓN HTTP
# ======================================================
def _post(path: str, payload: dict):
    url = BASE_URL + path
    signed = _sign(payload)
    r = requests.post(url, data=signed, timeout=10)
    try:
        data = r.json()
    except Exception:
        logger.error(f"Error parsing JSON from Bybit: {r.text}")
        return None
    return data


def _get(path: str, payload: dict):
    url = BASE_URL + path
    signed = _sign(payload)
    r = requests.get(url, params=signed, timeout=10)
    try:
        data = r.json()
    except Exception:
        logger.error(f"Error parsing JSON from Bybit: {r.text}")
        return None
    return data


# ============================================================
# ✅ FUNCIÓN CORREGIDA — SIEMPRE DEVUELVE DataFrame o None
# ============================================================


def get_ohlcv_data(
    symbol: str, timeframe: str = None, interval: str = None, limit: int = 200
):
    """
    Compatibilidad total:
    - timeframe (nuevo)
    - interval (legacy)
    Devuelve siempre DataFrame o None
    """
    try:
        tf = timeframe or interval
        if not tf:
            logger.error("❌ get_ohlcv_data llamado sin timeframe/interval")
            return None

        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)

        if not ohlcv or not isinstance(ohlcv, list):
            logger.error(f"❌ OHLCV inválido para {symbol} ({tf})")
            return None

        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        if df.empty:
            logger.warning(f"⚠️ DataFrame vacío para {symbol} ({tf})")
            return None

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df.dropna(inplace=True)

        return df if not df.empty else None

    except Exception as e:
        logger.error(
            f"❌ Error obteniendo OHLCV {symbol} ({timeframe or interval}): {e}",
            exc_info=True,
        )
        return None


# ======================================================
# 📌 POSICIONES ABIERTAS
# ======================================================
"""def get_open_positions(symbol: str = None):
    params = {"category": "linear"}
    if symbol:
        params["symbol"] = symbol
    data = _get("/v5/position/list", params)
    if not data or data.get("retCode") != 0:
        logger.error(f"Error get_open_positions: {data}")
        return []
    return data["result"]["list"]""" """"""


# ======================================================
# 📌 OBTENER PRECIO ACTUAL
# ======================================================
def get_last_price(symbol: str):
    data = _get("/v5/market/tickers", {"category": "linear", "symbol": symbol})
    if not data or data.get("retCode") != 0:
        logger.error(f"Error ticker {symbol}: {data}")
        return None
    try:
        return float(data["result"]["list"][0]["lastPrice"])
    except Exception:
        return None


# ======================================================
# 📉 CIERRE DE POSICIÓN
# ======================================================
def close_position(symbol: str):
    """
    Cierra cualquier posición abierta en el símbolo usando reduceOnly.
    """
    logger.info(f"🔻 Cerrando posición en {symbol}…")

    pos_list = get_open_positions(symbol)
    if not pos_list:
        logger.info(f"➡️ No hay posición abierta en {symbol}")
        return True

    pos = pos_list[0]
    side = "Sell" if pos["side"] == "Buy" else "Buy"
    qty = pos["size"]

    payload = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": qty,
        "reduceOnly": True,
        "timeInForce": "IOC",
    }

    data = _post("/v5/order/create", payload)
    if data and data.get("retCode") == 0:
        logger.info(f"✔ Posición cerrada correctamente: {symbol}")
        return True

    logger.error(f"❌ Error al cerrar posición: {data}")
    return False


# ======================================================
# 🔄 REVERSAR POSICIÓN
# ======================================================
def reverse_position(symbol: str):
    """
    Cierra la posición y abre una nueva al lado contrario con mismo tamaño.
    """
    logger.info(f"🔄 Iniciando reversión de {symbol}…")

    pos_list = get_open_positions(symbol)
    if not pos_list:
        logger.info(f"No hay posición para revertir -> nada que hacer.")
        return False

    pos = pos_list[0]
    current_side = pos["side"]
    qty = float(pos["size"])

    opposite_side = "Sell" if current_side == "Buy" else "Buy"

    # 1️⃣ Cerrar posición actual
    if not close_position(symbol):
        logger.error("❌ No se pudo cerrar la posición para revertir.")
        return False

    time.sleep(0.8)

    # 2️⃣ Abrir en el sentido contrario
    payload = {
        "category": "linear",
        "symbol": symbol,
        "side": opposite_side,
        "orderType": "Market",
        "qty": qty,
        "timeInForce": "IOC",
        "reduceOnly": False,
    }

    data = _post("/v5/order/create", payload)
    if data and data.get("retCode") == 0:
        logger.info("✔ Reversión completada correctamente.")
        return True

    logger.error(f"❌ Error al revertir posición: {data}")
    return False


# ======================================================
# 🚀 ABRIR POSICIÓN DE MERCADO (valor en USDT)
# ======================================================
def place_market_order(symbol: str, side: str, usdt: float, leverage: int = 20):
    """
    Abre una posición usando un valor fijo en USDT (ej: 3 USDT con x20).
    """
    last = get_last_price(symbol)
    if not last:
        logger.error("No se pudo obtener precio para abrir posición.")
        return False

    qty = round((usdt * leverage) / last, 6)

    payload = {
        "category": "linear",
        "symbol": symbol,
        "side": "Buy" if side.lower() == "long" else "Sell",
        "orderType": "Market",
        "qty": qty,
        "timeInForce": "IOC",
        "reduceOnly": False,
    }

    data = _post("/v5/order/create", payload)
    if data and data.get("retCode") == 0:
        logger.info(f"✔ Orden de mercado abierta correctamente: {symbol} {side}")
        return True

    logger.error(f"❌ Error al abrir orden de mercado: {data}")
    return False


# services/bybit_service/bybit_client.py
import logging
from config import BYBIT_SETTLE_COIN

logger = logging.getLogger("bybit_client")

# ... tu resto del archivo queda igual ...


async def get_open_positions(symbol: str | None = None, settle_coin: str | None = None):
    """
    Retorna lista de posiciones abiertas.
    - ES ASYNC para que 'await get_open_positions()' sea válido.
    - Bybit requiere symbol o settleCoin => usamos settleCoin=USDT por defecto.
    """
    settle_coin = settle_coin or BYBIT_SETTLE_COIN or "USDT"

    try:
        # ⚠️ Ajusta esto a TU cliente real.
        # Si usas pybit: session.get_positions(category="linear", settleCoin=settle_coin, symbol=symbol)
        # Si tienes ya una función sync interna, llámala aquí.

        params = {"category": "linear", "settleCoin": settle_coin}
        if symbol:
            params["symbol"] = symbol

        if isinstance(res, dict) and res.get("retCode") != 0:
            logger.error(f"Error get_open_positions: {res}")
            return []

        # Normaliza salida
        result = res.get("result", {}) if isinstance(res, dict) else {}
        positions = result.get("list", []) if isinstance(result, dict) else []
        return positions

    except Exception as e:
        logger.exception(f"❌ Error get_open_positions: {e}")
        return []
