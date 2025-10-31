# bybit_api.py - VERSIÓN COMPLETA CORREGIDA
"""
Cliente para API de Bybit - Trading Bot v2 - CON HEALTH MONITOR
"""
import logging
import asyncio
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode
import aiohttp

# ✅ NUEVO IMPORT
from health_monitor import health_monitor

logger = logging.getLogger(__name__)

class BybitClient:
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.api_key = None
        self.api_secret = None
        self.session = None
        self.is_initialized = False
        self.total_api_calls = 0
        self.failed_api_calls = 0

    async def is_connected(self):
        """Verifica si está conectado a Bybit - CON HEALTH MONITOR"""
        try:
            if not self.is_initialized or not self.session:
                return False
            
            # Test real de conexión
            test_result = await self.get_ticker("BTCUSDT")
            connected = test_result is not None
            
            # ✅ NUEVO: Registrar estado de conexión
            if not connected:
                health_monitor.record_connection_issue('bybit_api', 'Test de conexión falló')
            else:
                # Si estaba desconectado y ahora está conectado, registrar reconexión
                if not health_monitor.connection_status.get('bybit_api', True):
                    health_monitor.record_reconnect_attempt('bybit_api', True)
            
            return connected
        except Exception as e:
            logger.error(f"❌ Error verificando conexión Bybit: {e}")
            health_monitor.record_connection_issue('bybit_api', f"Error conexión: {e}")
            return False

    async def initialize(self):
        """Inicializa el cliente de Bybit para Linear - CON HEALTH MONITOR"""
        try:
            from config import BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_CATEGORY
            
            self.api_key = BYBIT_API_KEY
            self.api_secret = BYBIT_API_SECRET
            self.category = BYBIT_CATEGORY or "linear"

            if not self.api_key or not self.api_secret:
                logger.warning("⚠️ Credenciales de Bybit no configuradas")
                health_monitor.record_error("Credenciales de Bybit no configuradas", "Bybit Initialization")
                return False

            self.session = aiohttp.ClientSession()
            self.is_initialized = True

            # Test de conexión con Linear
            test_result = await self.get_ticker("BTCUSDT")
            if test_result:
                logger.info(f"✅ Cliente Bybit inicializado correctamente (Category: {self.category})")
                # ✅ NUEVO: Registrar inicialización exitosa
                health_monitor.record_reconnect_attempt('bybit_api', True)
                return True
            else:
                logger.error("❌ Error conectando con Bybit Linear")
                health_monitor.record_connection_issue('bybit_api', 'Inicialización falló')
                return False

        except Exception as e:
            logger.error(f"❌ Error inicializando Bybit: {e}")
            health_monitor.record_error(str(e), "Bybit Initialization")
            return False

    def _generate_signature(self, params: Dict) -> str:
        """Genera firma para autenticación API - CORREGIDO"""
        try:
            # ✅ CORRECCIÓN: Ordenar parámetros alfabéticamente
            param_str = ""
            if params:
                sorted_params = sorted(params.items())
                param_str = "&".join([f"{k}={v}" for k, v in sorted_params])
            
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            
            # ✅ CORRECCIÓN: Payload correcto para firma
            signature_payload = timestamp + self.api_key + recv_window + param_str
            
            signature = hmac.new(
                bytes(self.api_secret, "utf-8"),
                bytes(signature_payload, "utf-8"),
                hashlib.sha256,
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            logger.error(f"❌ Error generando firma: {e}")
            health_monitor.record_error(str(e), "generate_signature")
            return ""

    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Obtiene ticker de un símbolo en Linear"""
        try:
            if not self.is_initialized:
                await self.initialize()

            self.total_api_calls += 1
            health_monitor.record_bybit_api_call(f"get_ticker_{symbol}")

            url = f"{self.base_url}/v5/market/tickers"
            params = {
                "category": "linear",
                "symbol": symbol
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0 and data["result"]["list"]:
                        return data["result"]["list"][0]
                    else:
                        logger.warning(f"⚠️ No data for {symbol}: {data.get('retMsg', 'Unknown error')}")
                        self.failed_api_calls += 1
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} for {symbol}")
                    self.failed_api_calls += 1
                    health_monitor.record_connection_issue('bybit_api', f"HTTP {response.status} en get_ticker")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting ticker for {symbol}: {e}")
            self.failed_api_calls += 1
            health_monitor.record_error(str(e), f"get_ticker {symbol}")
            return None

    async def get_account_balance(self) -> Optional[Dict]:
        """Obtiene balance de la cuenta - CORREGIDO"""
        try:
            if not self.is_initialized:
                await self.initialize()

            self.total_api_calls += 1
            health_monitor.record_bybit_api_call("get_account_balance")

            timestamp = str(int(time.time() * 1000))
            
            params = {
                "accountType": "UNIFIED",
                "coin": "USDT"
            }

            signature = self._generate_signature(params)
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": "5000",
            }

            url = f"{self.base_url}/v5/account/wallet-balance"

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0:
                        return data["result"]
                    else:
                        logger.error(f"❌ API error getting balance: {data.get('retMsg', 'Unknown error')}")
                        self.failed_api_calls += 1
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} getting balance")
                    self.failed_api_calls += 1
                    health_monitor.record_connection_issue('bybit_api', f"HTTP {response.status} en get_balance")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting account balance: {e}")
            self.failed_api_calls += 1
            health_monitor.record_error(str(e), "get_account_balance")
            return None

    async def get_open_positions(self) -> Optional[List]:
        """Obtiene posiciones abiertas - CORREGIDO"""
        try:
            if not self.is_initialized:
                await self.initialize()

            self.total_api_calls += 1
            health_monitor.record_bybit_api_call("get_open_positions")

            timestamp = str(int(time.time() * 1000))
            
            params = {
                "category": "linear",
                "settleCoin": "USDT"
            }

            signature = self._generate_signature(params)
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": "5000",
            }

            url = f"{self.base_url}/v5/position/list"

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["retCode"] == 0:
                        return data["result"]["list"]
                    else:
                        if data["retCode"] == 10001:  # No position
                            return []
                        logger.warning(f"⚠️ API error getting positions: {data.get('retMsg', 'Unknown error')}")
                        self.failed_api_calls += 1
                        return None
                else:
                    logger.error(f"❌ HTTP error {response.status} getting positions")
                    self.failed_api_calls += 1
                    health_monitor.record_connection_issue('bybit_api', f"HTTP {response.status} en get_positions")
                    return None

        except Exception as e:
            logger.error(f"❌ Error getting open positions: {e}")
            self.failed_api_calls += 1
            health_monitor.record_error(str(e), "get_open_positions")
            return None

    # ... otros métodos se mantienen igual ...

# Instancia global
bybit_client = BybitClient()