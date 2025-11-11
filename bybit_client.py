"""
bybit_client.py — versión final verificada (producción 2025)
------------------------------------------------------------
Cliente unificado Bybit API v5 (UTA / Real / Testnet)
- Firma HMAC correcta (parámetros ordenados alfabéticamente)
- Compatible con análisis técnico y monitoreo de posiciones
- Integrado con operación y logging del sistema
------------------------------------------------------------
"""

import os
import time
import hmac
import hashlib
import requests
import logging
import pandas as pd
from urllib.parse import urlencode
from dotenv import load_dotenv
from config import (
    BYBIT_API_KEY,
    BYBIT_API_SECRET,
    SIMULATION_MODE,
    BYBIT_TESTNET,
)

# ================================================================
# 🧭 Configuración global
# ================================================================
load_dotenv()
logger = logging.getLogger("bybit_client")

BYBIT_ENDPOINT = (
    "https://api-testnet.bybit.com"
    if (SIMULATION_MODE or str(BYBIT_TESTNET).lower() == "true")
    else "https://api.bybit.com"
)


# ================================================================
# 🔐 Firma HMAC-SHA256 (orden alfabético)
# ================================================================
def _generate_signature(params: dict) -> str:
    sorted_params = sorted(params.items())
    param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    return hmac.new(
        bytes(BYBIT_API_SECRET, "utf-8"),
        param_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ================================================================
# 🌐 Request genérico firmado
# ================================================================
def _make_request(endpoint: str, params: dict) -> dict:
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    base_params = {
        "api_key": BYBIT_API_KEY,
        "timestamp": timestamp,
        "recvWindow": recv_window,
    }

    all_params = {**params, **base_params}
    all_params["sign"] = _generate_signature(all_params)

    url = f"{BYBIT_ENDPOINT}/v5/{endpoint}?{urlencode(all_params)}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        logger.info(f"📡 {endpoint}: retCode={data.get('retCode')} {data.get('retMsg')}")
        return data
    except Exception as e:
        logger.error(f"❌ Error en request {endpoint}: {e}")
        return {"retCode": -1, "retMsg": str(e)}


# ================================================================
# 📊 Obtener datos OHLCV
# ================================================================
def get_ohlcv_data(symbol: str, interval: str = "5", limit: int = 200):
    """Obtiene velas OHLCV (mercado linear USDT)."""
    try:
        url = f"{BYBIT_ENDPOINT}/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("retCode") != 0:
            logger.warning(f"⚠️ Error Bybit OHLCV: {data}")
            return None

        rows = data["result"].get("list", [])
        if not rows:
            logger.warning(f"⚠️ Sin datos OHLCV para {symbol}")
            return None

        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
        df = df.sort_values("timestamp")
        logger.info(f"📈 {symbol}: {len(df)} velas ({interval}m) procesadas correctamente.")
        return df

    except Exception as e:
        logger.error(f"❌ Error en get_ohlcv_data({symbol}): {e}")
        return None


# ================================================================
# 💼 Obtener información de cuenta
# ================================================================
def get_account_info():
    """Devuelve balance general de cuenta UTA."""
    if SIMULATION_MODE:
        logger.info("💬 [SIM] Modo simulación activo (get_account_info).")
        return {"totalEquity": "10000", "totalWalletBalance": "9500", "availableBalance": "8500"}

    data = _make_request("account/wallet-balance", {"accountType": "UNIFIED"})
    if data.get("retCode") == 0:
        return data["result"]["list"][0]
    return {"error": data.get("retMsg", "Error desconocido")}


# ================================================================
# 📈 Obtener posiciones abiertas
# ================================================================
def get_open_positions():
    """Devuelve posiciones abiertas (reales o simuladas)."""
    if SIMULATION_MODE:
        logger.info("💬 [SIM] Retornando posiciones simuladas.")
        return [
            {"symbol": "BTCUSDT", "side": "Buy", "size": "0.1", "entryPrice": "68000", "leverage": "20"},
            {"symbol": "ETHUSDT", "side": "Sell", "size": "1", "entryPrice": "3600", "leverage": "20"},
        ]

    data = _make_request("position/list", {"category": "linear", "settleCoin": "USDT"})
    if data.get("retCode") != 0:
        logger.error(f"❌ Error en get_open_positions(): {data.get('retMsg')}")
        return []

    positions = [
        p for p in data["result"].get("list", []) if float(p.get("size", 0)) > 0
    ]
    logger.info(f"📊 {len(positions)} posiciones abiertas detectadas.")
    return positions


# ================================================================
# 🧾 Obtener órdenes abiertas
# ================================================================
def get_open_orders():
    """Devuelve órdenes pendientes (solo lineales)."""
    data = _make_request("order/realtime", {"category": "linear", "settleCoin": "USDT", "openOnly": "1"})
    if data.get("retCode") != 0:
        logger.warning(f"⚠️ Error al obtener órdenes: {data.get('retMsg')}")
        return []
    return data["result"].get("list", [])


# ================================================================
# 🧮 Formatear reportes para Telegram
# ================================================================
def format_account_summary(account_info: dict, positions: list) -> str:
    total_pnl = sum(float(p.get("unrealisedPnl", 0)) for p in positions)
    equity = account_info.get("totalEquity", "0")
    balance = account_info.get("totalWalletBalance", "0")
    available = account_info.get("availableBalance", "0")
    return (
        f"💼 **RESUMEN DE CUENTA**\n"
        f"┌ Balance Total: ${balance}\n"
        f"├ Equity: ${equity}\n"
        f"├ Disponible: ${available}\n"
        f"├ Posiciones Abiertas: {len(positions)}\n"
        f"└ P&L Total: ${total_pnl:.2f}\n"
    )


def format_position_message(position: dict) -> str:
    side_emoji = "🟢" if position["side"].lower() == "buy" else "🔴"
    pnl = float(position.get("unrealisedPnl", 0))
    pnl_emoji = "📈" if pnl >= 0 else "📉"
    return (
        f"{side_emoji} **{position['symbol']}**\n"
        f"┌ Dirección: {position['side']}\n"
        f"├ Tamaño: {position['size']}\n"
        f"├ Precio Entrada: ${position['entryPrice']}\n"
        f"├ Precio Actual: ${position.get('markPrice', 'N/A')}\n"
        f"├ Apalancamiento: {position['leverage']}x\n"
        f"├ P&L: {pnl_emoji} ${pnl:.2f}\n"
        f"└ Precio Liq: ${position.get('liqPrice', 'N/A')}\n"
    )


# ================================================================
# 🔍 Prueba local
# ================================================================
if __name__ == "__main__":
    print("🚀 Test BybitClient (v15 verified final)")
    acc = get_account_info()
    pos = get_open_positions()
    print(format_account_summary(acc, pos))
    for p in pos:
        print(format_position_message(p))
