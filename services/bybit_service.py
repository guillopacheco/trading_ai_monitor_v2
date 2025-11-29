"""
bybit_service.py
----------------
Capa de servicio que abstrae completamente el uso de la API de Bybit.

Objetivos:
- Ser la única forma en que otros módulos acceden a datos de mercado,
  posiciones abiertas y operación de órdenes.
- Mantener compatibilidad directa con el módulo bybit_client.py.
- Entregar una API estable y documentada, independiente del motor técnico.
- Manejo centralizado de errores, reconexión y validación de parámetros.

Este módulo NO contiene lógica técnica (tendencias, divergencias, entradas).
Solo conecta con Bybit.
"""

import logging
from typing import Optional, Dict, Any, List

from services.bybit_client import (
    get_ohlcv_data,
    get_symbol_price,
    get_positions,
    place_order_market,
    close_position_market,
)

logger = logging.getLogger("bybit_service")


# ================================================================
# 🔵 Servicio: Datos de Mercado
# ================================================================
async def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 200) -> Optional[List[Dict]]:
    """
    Obtiene OHLCV desde Bybit a través de bybit_client.
    Este método encapsula validación y manejo de errores.

    Returns:
        Lista de velas o None si falla.
    """
    try:
        data = get_ohlcv_data(symbol, timeframe, limit)
        if not data:
            logger.warning(f"⚠️ No se recibieron datos OHLCV para {symbol} ({timeframe}).")
            return None
        return data
    except Exception as e:
        logger.error(f"❌ Error obteniendo OHLCV de Bybit: {e}")
        return None


async def fetch_price(symbol: str) -> Optional[float]:
    """
    Devuelve el precio actual del símbolo.
    """
    try:
        price = get_symbol_price(symbol)
        return float(price)
    except Exception as e:
        logger.error(f"❌ Error obteniendo precio de {symbol}: {e}")
        return None


# ================================================================
# 🔵 Servicio: Posiciones
# ================================================================
async def fetch_positions() -> List[Dict[str, Any]]:
    """
    Devuelve la lista de posiciones abiertas en Bybit.
    """
    try:
        pos = get_positions()
        if pos is None:
            return []
        return pos
    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones: {e}")
        return []


async def fetch_position(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Devuelve la posición actual de un símbolo específico.
    """
    try:
        positions = get_positions()
        if not positions:
            return None

        for p in positions:
            if p.get("symbol") == symbol:
                return p

        return None
    except Exception as e:
        logger.error(f"❌ Error obteniendo posición para {symbol}: {e}")
        return None


# ================================================================
# 🔵 Servicio: Órdenes (capa segura para automatización futura)
# ================================================================
async def open_market_order(symbol: str, side: str, size: float, leverage: int = 20) -> Optional[Dict]:
    """
    Abre una posición de mercado con apalancamiento.

    Args:
        symbol  → ejemplo: "BTCUSDT"
        side    → "Buy" o "Sell"
        size    → cantidad en contrato
        leverage → normalmente 20 para futuros

    Returns:
        dict con detalles de la orden o None si falla
    """
    try:
        order = place_order_market(symbol, side, size, leverage)
        logger.info(f"🟢 Orden de mercado enviada: {symbol} {side} x{leverage} size={size}")
        return order
    except Exception as e:
        logger.error(f"❌ Error enviando orden de mercado: {e}")
        return None


async def close_market_order(symbol: str, side: str, size: float) -> Optional[Dict]:
    """
    Cierra una posición de mercado.

    Args:
        side = "Buy" o "Sell" según la dirección del cierre

    Returns:
        dict o None
    """
    try:
        order = close_position_market(symbol, side, size)
        logger.info(f"🟡 Orden de cierre enviada: {symbol} {side} size={size}")
        return order
    except Exception as e:
        logger.error(f"❌ Error cerrando posición: {e}")
        return None


# ================================================================
# 🔵 Utilidades
# ================================================================
async def is_symbol_active(symbol: str) -> bool:
    """
    Comprueba si hay datos y precio para el símbolo.
    """
    price = await fetch_price(symbol)
    if price is None:
        return False

    ohlcv = await fetch_ohlcv(symbol, "1h", limit=3)
    if ohlcv is None:
        return False

    return True


# ================================================================
# 🔵 Prueba manual
# ================================================================
if __name__ == "__main__":
    import asyncio

    async def test():
        print(await fetch_price("BTCUSDT"))
        print(await fetch_ohlcv("BTCUSDT", "1h"))
        print(await fetch_positions())

    asyncio.run(test())
