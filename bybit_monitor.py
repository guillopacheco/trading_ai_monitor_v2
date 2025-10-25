"""
Monitor de operaciones abiertas en Bybit - Solo lectura
"""
import logging
from typing import Dict, List, Optional
from pybit.unified_trading import HTTP
from config import BYBIT_API_KEY, BYBIT_API_SECRET

logger = logging.getLogger(__name__)

class BybitMonitor:
    """Monitor de solo lectura para operaciones en Bybit"""
    
    def __init__(self):
        self.session = None
        self._initialize_session()
    
    def _initialize_session(self):
        """Inicializa sesión de solo lectura con Bybit"""
        try:
            if BYBIT_API_KEY and BYBIT_API_SECRET:
                self.session = HTTP(
                    api_key=BYBIT_API_KEY,
                    api_secret=BYBIT_API_SECRET,
                    testnet=False  # Cambiar a True para testing
                )
                logger.info("✅ Monitor Bybit inicializado (solo lectura)")
            else:
                logger.warning("⚠️ API Keys de Bybit no configuradas - Monitor desactivado")
                self.session = None
        except Exception as e:
            logger.error(f"❌ Error inicializando monitor Bybit: {e}")
            self.session = None
    
    async def get_open_positions(self) -> List[Dict]:
        """Obtiene posiciones abiertas de Bybit"""
        try:
            if not self.session:
                return []
            
            # Obtener posiciones activas
            response = self.session.get_positions(
                category="linear",
                settleCoin="USDT"
            )
            
            if response['retCode'] == 0:
                open_positions = []
                for position in response['result']['list']:
                    if float(position['size']) > 0:  # Posición activa
                        open_positions.append({
                            'symbol': position['symbol'],
                            'side': position['side'].upper(),  # BUY/SELL
                            'size': float(position['size']),
                            'entry_price': float(position['avgPrice']),
                            'leverage': int(position['leverage']),
                            'liq_price': float(position['liqPrice']),
                            'unrealised_pnl': float(position['unrealisedPnl']),
                            'created_time': position['createdTime']
                        })
                
                logger.info(f"📊 {len(open_positions)} posiciones abiertas detectadas")
                return open_positions
            else:
                logger.error(f"❌ Error API Bybit: {response['retMsg']}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo posiciones de Bybit: {e}")
            return []
    
    async def get_account_balance(self) -> Optional[float]:
        """Obtiene balance de la cuenta"""
        try:
            if not self.session:
                return None
            
            response = self.session.get_wallet_balance(accountType="UNIFIED")
            
            if response['retCode'] == 0:
                total_equity = float(response['result']['list'][0]['totalEquity'])
                logger.debug(f"💰 Balance total: {total_equity} USDT")
                return total_equity
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance: {e}")
            return None

# Instancia global
bybit_monitor = BybitMonitor()