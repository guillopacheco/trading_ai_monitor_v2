# bybit_api.py
"""
Cliente para API de Bybit - Trading Bot v2
"""
import logging
import asyncio
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode
import aiohttp

logger = logging.getLogger(__name__)

class BybitClient:
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.api_key = None
        self.api_secret = None
        self.session = None
        self.is_initialized = False

    def is_connected(self):
        """Verifica si está conectado a Bybit"""

        return self.session is not None

    async def connect(self):
        """Conecta a Bybit"""
        try:
            # Tu lógica de conexión existente
            self.is_connected_flag = True
            return True
        except Exception as e:
            logger.error(f"Error conectando a Bybit: {e}")
            return False

    async def initialize(self):
        """Inicializa el cliente de Bybit para Linear"""
        try:
            from config import BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_CATEGORY
            
            self.api_key = BYBIT_API_KEY
            self.api_secret = BYBIT_API_SECRET
            self.category = BYBIT_CATEGORY or "linear"  # ← USAR LINEAR

            if not self.api_key or not self.api_secret:
                logger.warning("⚠️ Credenciales de Bybit no configuradas")
                return False

            self.session = aiohttp.ClientSession()
            self.is_initialized = True

            # Test de conexión con Linear
            test_result = await self.get_ticker("BTCUSDT")
            if test_result:
                logger.info(f"✅ Cliente Bybit inicializado correctamente (Category: {self.category})")
                return True
            else:
                logger.error("❌ Error conectando con Bybit Linear")
                return False

        except Exception as e:
            logger.error(f"❌ Error inicializando Bybit: {e}")
            return False

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Obtiene ticker de un símbolo en Linear"""
        try:
            if not self.is_initialized:
                await self.initialize()

            url = f"{self.base_url}/v5/market/tickers"
            params = {
                "category": "linear",  # ← USAR LA CATEGORÍA CONFIGURADA
                "symbol": symbol
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0 and data["result"]["list"]:
                        return data["result"]["list"][0]
                    else:
                        logger.warning(f"⚠️ No data for {symbol} in {self.category}: {data.get('retMsg', 'Unknown error')}")
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} for {symbol}")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting ticker for {symbol}: {e}")
            return None

    async def get_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> Optional[List]:
        """Obtiene datos de velas (klines)"""
        try:
            if not self.is_initialized:
                await self.initialize()

            url = f"{self.base_url}/v5/market/kline"
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0:
                        return data["result"]["list"]
                    else:
                        logger.warning(
                            f"⚠️ No kline data for {symbol}: {data.get('retMsg', 'Unknown error')}"
                        )
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} for klines {symbol}")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting klines for {symbol}: {e}")
            return None

    async def get_account_balance(self) -> Optional[Dict]:
        """Obtiene balance de la cuenta"""
        try:
            if not self.is_initialized:
                await self.initialize()

            timestamp = str(int(time.time() * 1000))
            params = {"accountType": "UNIFIED", "timestamp": timestamp}

            signature = self._generate_signature(params)
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": "5000",
            }

            url = f"{self.base_url}/v5/account/wallet-balance"

            async with self.session.get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0:
                        return data["result"]
                    else:
                        logger.error(
                            f"❌ API error getting balance: {data.get('retMsg', 'Unknown error')}"
                        )
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} getting balance")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting account balance: {e}")
            return None

    async def get_open_positions(self) -> Optional[List]:
        """Obtiene posiciones abiertas"""
        try:
            if not self.is_initialized:
                await self.initialize()

            timestamp = str(int(time.time() * 1000))
            params = {"category": "linear", "timestamp": timestamp}

            signature = self._generate_signature(params)
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": "5000",
            }

            url = f"{self.base_url}/v5/position/list"

            async with self.session.get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0:
                        return data["result"]["list"]
                    else:
                        # Puede ser normal si no hay posiciones
                        if data["retCode"] == 10001:  # No position
                            return []
                        logger.warning(
                            f"⚠️ API error getting positions: {data.get('retMsg', 'Unknown error')}"
                        )
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} getting positions")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting open positions: {e}")
            return None

    async def place_order(self, order_data: Dict) -> Optional[Dict]:
        """Coloca una orden en Bybit"""
        try:
            if not self.is_initialized:
                await self.initialize()

            timestamp = str(int(time.time() * 1000))
            params = {
                "category": "linear",
                "symbol": order_data.get("symbol"),
                "side": order_data.get("side"),
                "orderType": order_data.get("orderType", "Market"),
                "qty": order_data.get("qty"),
                "timestamp": timestamp,
            }

            # Agregar precio si es orden limit
            if order_data.get("orderType") == "Limit":
                params["price"] = order_data.get("price")

            signature = self._generate_signature(params)
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": "5000",
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/v5/order/create"

            async with self.session.post(url, json=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0:
                        logger.info(
                            f"✅ Orden colocada: {order_data.get('symbol')} {order_data.get('side')}"
                        )
                        return data["result"]
                    else:
                        logger.error(
                            f"❌ Error placing order: {data.get('retMsg', 'Unknown error')}"
                        )
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} placing order")
                    return None

        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return None

    async def close_position(self, symbol: str) -> Optional[Dict]:
        """Cierra una posición"""
        try:
            # Primero obtener la posición actual
            positions = await self.get_open_positions()
            if not positions:
                logger.info(f"ℹ️ No open position for {symbol}")
                return None

            position = next((p for p in positions if p["symbol"] == symbol), None)
            if not position:
                logger.info(f"ℹ️ No open position for {symbol}")
                return None

            # Determinar side opuesto para cerrar
            current_side = position["side"]
            close_side = "Sell" if current_side == "Buy" else "Buy"

            order_data = {
                "symbol": symbol,
                "side": close_side,
                "orderType": "Market",
                "qty": position["size"],
            }

            return await self.place_order(order_data)

        except Exception as e:
            logger.error(f"❌ Error closing position for {symbol}: {e}")
            return None

    async def reconnect(self):
        """Reconecta el cliente"""
        try:
            if self.session:
                await self.session.close()
            self.session = aiohttp.ClientSession()
            logger.info("✅ Cliente Bybit reconectado")
        except Exception as e:
            logger.error(f"❌ Error reconectando Bybit: {e}")

    async def close(self):
        """Cierra la conexión"""
        try:
            if self.session:
                await self.session.close()
            logger.info("✅ Cliente Bybit cerrado")
        except Exception as e:
            logger.error(f"❌ Error cerrando cliente Bybit: {e}")


# Instancia global
bybit_client = BybitClient()
