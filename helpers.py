"""
helpers.py — Utilidades generales limpias y optimizadas
------------------------------------------------------------
Funciones auxiliares realmente necesarias y compatibles con
toda la arquitectura final del sistema.

Incluye:
- Normalización de símbolos
- Normalización de direcciones LONG/SHORT
- Cálculo de ROI
- Cálculo de diferencia porcentual
- Timestamp seguro
- Redondeo seguro
------------------------------------------------------------
"""

import logging
from datetime import datetime

logger = logging.getLogger("helpers")


# ================================================================
# 🔤 Normalizar símbolo (ej: BTC/USDT → BTCUSDT)
# ================================================================
def normalize_symbol(symbol: str) -> str:
    """
    Normaliza un símbolo para uso en Bybit o análisis.
    """
    try:
        if not symbol:
            return ""
        symbol = symbol.upper().replace("/", "").replace("-", "")
        if not symbol.endswith("USDT"):
            symbol += "USDT"
        return symbol
    except Exception as e:
        logger.error(f"❌ Error normalizando símbolo: {e}")
        return symbol or ""


# ================================================================
# 🎯 Normalizar dirección (LONG / SHORT)
# ================================================================
def normalize_direction(direction: str) -> str:
    """
    Devuelve 'long', 'short' o 'unknown'.
    """
    try:
        direction = direction.strip().lower()
        if "long" in direction:
            return "long"
        if "short" in direction:
            return "short"
        return "unknown"
    except Exception:
        return "unknown"


# ================================================================
# 💹 ROI (Return on Investment)
# ================================================================
def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int = 20) -> float:
    """
    Calcula el ROI considerando dirección y apalancamiento.
    ROI = ((actual - entrada) / entrada) * 100 * leverage
    Para SHORT se invierte el signo.
    """
    try:
        if entry_price <= 0 or current_price <= 0:
            return 0.0

        change = ((current_price - entry_price) / entry_price) * 100
        roi = change * leverage

        if direction.lower().startswith("short"):
            roi *= -1

        return round(roi, 2)
    except Exception as e:
        logger.error(f"❌ Error calculando ROI: {e}")
        return 0.0


# ================================================================
# 📉 Diferencia porcentual
# ================================================================
def percent_diff(a: float, b: float) -> float:
    """
    Diferencia porcentual entre dos valores.
    """
    try:
        if a == 0:
            return 0.0
        return round(((b - a) / a) * 100, 2)
    except Exception as e:
        logger.error(f"❌ Error calculando diferencia porcentual: {e}")
        return 0.0


# ================================================================
# 🕒 Timestamp legible
# ================================================================
def format_timestamp(ts: float | str | None = None) -> str:
    """
    Devuelve un timestamp legible para BD y logs.
    """
    try:
        if ts is None:
            return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(ts, (float, int)):
            return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        return str(ts)
    except Exception as e:
        logger.error(f"❌ Error formateando timestamp: {e}")
        return "N/A"


# ================================================================
# 🔢 Redondeo seguro
# ================================================================
def safe_round(value: float, decimals: int = 4) -> float:
    """
    Redondeo tolerante a errores.
    """
    try:
        return round(float(value), decimals)
    except Exception:
        return 0.0
