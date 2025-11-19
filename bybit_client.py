"""
bybit_client.py — versión final (2025)
-----------------------------------------------
Cliente oficial para Bybit API v5 (REST).

Características:
✔ Firma v5 correcta (HMAC-SHA256)
✔ Integrado con SIMULATION_MODE
✔ get_ohlcv_data() limpio compatible con trend_system_final
✔ Manejo robusto de posiciones
✔ Cliente estable para entorno VPS 24/7
-----------------------------------------------
"""

import os
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
    SIMULATION_MODE,
    BYBIT_ENDPOINT,
)

logger = logging.getLogger("bybit_client")


# ============================================================
# 🔐 Firma para API Bybit v5
# ============================================================

def _generate_signature(params: dict) -> str:
    """
    Firma los parámetros en orden alfabético según Bybit API v5.
    """
    sorted_params = sorted(params.items())
    qs = "&".join([f"{k}={v}" for k, v in sorted_params])
    return hmac.new(
        BYBIT_API_SECRET.encode("utf-8"),
        qs.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


# ============================================================
# 🌐 Request GET firmado
# ============================================================

def _make_request(endpoint: str, params: dict) -> dict:
    """
    Realiza request GET firmado para Bybit v5.
    """
    timestamp = str(int(time.time() * 1000))
    base = {
        "api_key": BYBIT_API_KEY,
        "timestamp": timestamp,
        "recvWindow": "5000"
    }

    full = {**params, **base}
    full["sign"] = _generate_signature(full)

    url = f"{BYBIT_ENDPOINT}/v5/{endpoint}?{urlencode(full)}"

    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        code = data.get("retCode")
        msg = data.get("retMsg", "")
        logger.info(f"📡 [{endpoint}] retCode={code} — {msg}")
        return data

    except Exception as e:
        logger.error(f"❌ Error en petición {endpoint}: {e}")
        return {"retCode": -1, "retMsg": str(e), "result": {}}


# ============================================================
# 📊 OHLCV (para análisis técnico)
# ============================================================

def get_ohlcv_data(symbol: str, interval: str = "5", limit: int = 200):
    """
    Obtiene velas OHLCV para análisis técnico.
    Compatible con trend_system_final.py.
    """

    try:
        url = f"{BYBIT_ENDPOINT}/v5/market/kline"

        params = {
            "category": "linear",
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data.get("retCode") != 0:
            logger.warning(f"⚠️ OHLCV error for {symbol}: {data}")
            return None

        rows = data["result"].get("list", [])
        if not rows:
            return None

        df = pd.DataFrame(
            rows,
            columns=[
                "timestamp", "open", "high", "low",
                "close", "volume", "turnover"
            ]
        )

        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df = df.sort_values("timestamp")
        return df

    except Exception as e:
        logger.error(f"❌ Error en get_ohlcv_data({symbol}): {e}")
        return None


# ============================================================
# 💼 Balance de cuenta
# ============================================================

def get_account_info():
    if SIMULATION_MODE:
        return {
            "totalEquity": "10000",
            "totalWalletBalance": "9500",
            "availableBalance": "8500",
        }

    data = _make_request("account/wallet-balance", {"accountType": "UNIFIED"})
    if data.get("retCode") == 0:
        return data["result"]["list"][0]

    return {"error": data.get("retMsg", "error")}


# ============================================================
# 📈 Obtener posiciones abiertas
# ============================================================

def get_open_positions():
    """
    Devuelve posiciones abiertas limpias y consistentes.
    """
    if SIMULATION_MODE:
        return [
            {"symbol": "BTCUSDT", "side": "Buy", "size": "0.1",
             "entryPrice": "68000", "markPrice": "68100",
             "leverage": "20", "unrealisedPnl": "5"},
            {"symbol": "ETHUSDT", "side": "Sell", "size": "1",
             "entryPrice": "3600", "markPrice": "3590",
             "leverage": "20", "unrealisedPnl": "10"},
        ]

    data = _make_request("position/list", {"category": "linear", "settleCoin": "USDT"})

    if data.get("retCode") != 0:
        return []

    result = data.get("result", {})
    positions = result.get("list", [])

    cleaned = []

    for p in positions:
        size = float(p.get("size", 0))
        if size <= 0:
            continue

        entry = p.get("entryPrice")
        avg  = p.get("avgPrice")

        # Fallback
        if not entry or entry == "0":
            if avg and float(avg) > 0:
                entry = avg
                p["entryPrice"] = avg
                logger.info(f"ℹ️ entryPrice corregido con avgPrice ({avg}) en {p['symbol']}")

        cleaned.append(p)

    return cleaned


# ============================================================
# 📄 Órdenes abiertas
# ============================================================

def get_open_orders():
    data = _make_request("order/realtime", {
        "category": "linear",
        "settleCoin": "USDT",
        "openOnly": "1"
    })

    if data.get("retCode") != 0:
        return []

    return data.get("result", {}).get("list", [])


# ============================================================
# 🧾 Formatos para Telegram
# ============================================================

def format_account_summary(account_info: dict, positions: list) -> str:
    pnl = sum(float(p.get("unrealisedPnl", 0)) for p in positions)

    return (
        f"💼 **Resumen de Cuenta**\n"
        f"• Balance: ${account_info.get('totalWalletBalance', '0')}\n"
        f"• Equity: ${account_info.get('totalEquity', '0')}\n"
        f"• Disponible: ${account_info.get('availableBalance', '0')}\n"
        f"• Posiciones: {len(positions)}\n"
        f"• PnL Total: ${pnl:.2f}\n"
    )


def format_position_message(p: dict) -> str:
    emoji = "🟢" if p["side"].lower() == "buy" else "🔴"
    pnl = float(p.get("unrealisedPnl", 0))
    p_emoji = "📈" if pnl >= 0 else "📉"

    return (
        f"{emoji} **{p['symbol']}**\n"
        f"• Dirección: {p['side']}\n"
        f"• Tamaño: {p.get('size')}\n"
        f"• Entrada: ${p.get('entryPrice')}\n"
        f"• Actual:  ${p.get('markPrice', 'N/A')}\n"
        f"• PnL: {p_emoji} ${pnl:.2f}\n"
        f"• Apalancamiento: {p.get('leverage')}x\n"
    )


# ============================================================
# 🧪 Test manual
# ============================================================

if __name__ == "__main__":
    print("🚀 Test Bybit Client (2025 final)")
    print(get_open_positions())
