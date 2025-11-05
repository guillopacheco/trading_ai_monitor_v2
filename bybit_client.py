import time
import hmac
import hashlib
import requests
import logging
from config import BYBIT_API_KEY, BYBIT_API_SECRET, SIMULATION_MODE

logger = logging.getLogger("bybit_client")

BASE_URL = "https://api.bybit.com"


# ================================================================
# 🔐 Generación de firma segura
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
# 📊 Obtener posiciones abiertas
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
        params = {"category": "linear", "settleCoin": "USDT", "limit": 20}
        params["api_key"] = BYBIT_API_KEY
        params["timestamp"] = int(time.time() * 1000)
        params["sign"] = generate_signature(params)

        response = requests.get(BASE_URL + endpoint, params=params, timeout=10)
        data = response.json()

        positions = []
        if "result" in data and "list" in data["result"]:
            for pos in data["result"]["list"]:
                if float(pos["size"]) > 0:
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
