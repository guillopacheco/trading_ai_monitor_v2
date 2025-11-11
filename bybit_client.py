# ================================================================
# bybit_client_v15_verified.py
# Cliente verificado para Bybit API v5 — Producción
# ================================================================

import os
import time
import hmac
import hashlib
import requests
import logging
from dotenv import load_dotenv
from urllib.parse import urlencode
from typing import Dict, List, Optional

# ================================================================
# 🔧 Configuración inicial
# ================================================================
load_dotenv()
logger = logging.getLogger("bybit_client")

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BYBIT_ENDPOINT = os.getenv("BYBIT_ENDPOINT", "https://api.bybit.com")
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "False").lower() == "true"


# ================================================================
# 🔐 Cliente principal
# ================================================================
class BybitClientVerified:
    """Cliente Bybit con firma manual validada y endpoints v5"""

    def __init__(self):
        if not BYBIT_API_KEY or not BYBIT_API_SECRET:
            raise ValueError("❌ Faltan credenciales BYBIT_API_KEY o BYBIT_API_SECRET en .env")

        self.api_key = BYBIT_API_KEY
        self.api_secret = BYBIT_API_SECRET
        self.base_url = f"{BYBIT_ENDPOINT}/v5"

        mode = "🧪 SIMULACIÓN" if SIMULATION_MODE else "💹 REAL"
        logger.info(f"✅ BybitClient iniciado en modo {mode}")

    # ============================================================
    # 🧾 Firma (signature)
    # ============================================================
    def _generate_signature(self, params: Dict) -> str:
        """Genera la firma ordenando alfabéticamente los parámetros"""
        sorted_params = sorted(params.items())
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(
            bytes(self.api_secret, "utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    # ============================================================
    # 🌐 Request genérico
    # ============================================================
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Ejecuta una solicitud GET firmada a Bybit"""
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"

        base_params = {
            "api_key": self.api_key,
            "timestamp": timestamp,
            "recvWindow": recv_window,
        }

        all_params = {**params, **base_params}
        all_params["sign"] = self._generate_signature(all_params)

        url = f"{self.base_url}/{endpoint}?{urlencode(all_params)}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            code = data.get("retCode")
            msg = data.get("retMsg")
            logger.info(f"🌐 Request {endpoint} → {code} ({msg})")
            return data

        except Exception as e:
            logger.error(f"❌ Error en request {endpoint}: {e}")
            return {"retCode": -1, "retMsg": str(e)}

    # ============================================================
    # 💰 Información de cuenta
    # ============================================================
    def get_account_info(self) -> Dict:
        """Obtiene información de la cuenta unificada"""
        if SIMULATION_MODE:
            return self._get_simulated_account()

        data = self._make_request("account/wallet-balance", {"accountType": "UNIFIED"})
        if data.get("retCode") == 0:
            return data["result"]["list"][0]
        else:
            return {"error": data.get("retMsg", "Error desconocido")}

    # ============================================================
    # 📈 Posiciones abiertas
    # ============================================================
    def get_open_positions(self) -> List[Dict]:
        """Devuelve las posiciones abiertas en contratos lineales USDT"""
        if SIMULATION_MODE:
            return self._get_simulated_positions()

        data = self._make_request("position/list", {"category": "linear", "settleCoin": "USDT"})
        if data.get("retCode") == 0:
            return [
                pos for pos in data["result"]["list"]
                if float(pos.get("size", 0)) > 0
            ]
        else:
            logger.warning(f"⚠️ Error al obtener posiciones: {data.get('retMsg')}")
            return []

    # ============================================================
    # 📋 Órdenes abiertas
    # ============================================================
    def get_open_orders(self) -> List[Dict]:
        """Devuelve las órdenes activas"""
        if SIMULATION_MODE:
            return []

        data = self._make_request("order/realtime", {"category": "linear", "settleCoin": "USDT"})
        if data.get("retCode") == 0:
            return data["result"]["list"]
        else:
            return []

    # ============================================================
    # 🧮 Formateadores
    # ============================================================
    def format_position_message(self, position: Dict) -> str:
        side_emoji = "🟢" if position["side"].lower() == "buy" else "🔴"
        pnl = float(position.get("unrealisedPnl", 0))
        pnl_emoji = "📈" if pnl >= 0 else "📉"

        msg = (
            f"{side_emoji} **{position['symbol']}**\n"
            f"┌ Dirección: {position['side']}\n"
            f"├ Tamaño: {position['size']}\n"
            f"├ Entrada: ${position['entryPrice']}\n"
            f"├ Actual: ${position.get('markPrice', 'N/A')}\n"
            f"├ Leverage: {position['leverage']}x\n"
            f"├ PnL: {pnl_emoji} ${pnl:.2f}\n"
            f"└ Liq: ${position.get('liqPrice', 'N/A')}\n"
        )
        return msg

    def format_account_summary(self, account_info: Dict, positions: List[Dict]) -> str:
        total_pnl = sum(float(p.get("unrealisedPnl", 0)) for p in positions)
        balance = account_info.get("totalWalletBalance", "0")
        equity = account_info.get("totalEquity", "0")
        available = account_info.get("availableBalance", "0")

        msg = (
            f"💼 **RESUMEN DE CUENTA**\n"
            f"┌ Balance: ${balance}\n"
            f"├ Equity: ${equity}\n"
            f"├ Disponible: ${available}\n"
            f"├ Posiciones: {len(positions)}\n"
            f"└ P&L Total: ${total_pnl:.2f}\n"
        )
        return msg

    # ============================================================
    # 🧪 Datos simulados
    # ============================================================
    def _get_simulated_positions(self):
        return [
            {
                "symbol": "BTCUSDT",
                "side": "Buy",
                "size": "0.01",
                "entryPrice": "45000.0",
                "leverage": "20",
                "unrealisedPnl": "150.50",
                "liqPrice": "42000.0",
                "markPrice": "45150.5"
            }
        ]

    def _get_simulated_account(self):
        return {
            "totalEquity": "10000.0",
            "totalWalletBalance": "9500.0",
            "availableBalance": "8500.0"
        }


# ================================================================
# 🧩 Ejemplo de uso (solo para prueba directa)
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = BybitClientVerified()

    account = client.get_account_info()
    positions = client.get_open_positions()

    print(client.format_account_summary(account, positions))
    for pos in positions:
        print(client.format_position_message(pos))
