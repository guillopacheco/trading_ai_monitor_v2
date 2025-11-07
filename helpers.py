"""
helpers.py
------------------------------------------------------------
Funciones auxiliares generales utilizadas en análisis,
monitoreo de operaciones y formateo de datos.
------------------------------------------------------------
"""

import logging
import random
import time
import requests
from datetime import datetime
from config import SIMULATION_MODE, BYBIT_TESTNET, BYBIT_API_KEY, BYBIT_API_SECRET

logger = logging.getLogger("helpers")

# ================================================================
# 🧩 Normalizar símbolo
# ================================================================
def normalize_symbol(symbol: str) -> str:
    """
    Limpia y normaliza un símbolo para uso en Bybit (ej: 'BTC/USDT' → 'BTCUSDT').
    """
    try:
        if not symbol:
            return ""
        symbol = symbol.upper().replace("/", "").replace("-", "")
        if symbol.endswith("USDT"):
            return symbol
        if "USDT" not in symbol:
            symbol += "USDT"
        return symbol
    except Exception as e:
        logger.error(f"❌ Error normalizando símbolo: {e}")
        return symbol or ""


# ================================================================
# 💰 Cálculo de ROI (Return on Investment)
# ================================================================
def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int = 20) -> float:
    """
    Calcula el ROI porcentual considerando dirección y apalancamiento.
    ROI = ((precio_actual - entrada) / entrada) * 100 * leverage
    """
    try:
        if entry_price <= 0 or current_price <= 0:
            return 0.0

        raw_change = ((current_price - entry_price) / entry_price) * 100
        roi = raw_change * leverage
        if direction.lower().startswith("short"):
            roi *= -1

        return round(roi, 2)
    except Exception as e:
        logger.error(f"❌ Error calculando ROI: {e}")
        return 0.0


# ================================================================
# 💹 Obtener precio actual del símbolo
# ================================================================
def get_current_price(symbol: str) -> float:
    """
    Obtiene el precio actual desde Bybit o simulado.
    """
    try:
        normalized = normalize_symbol(symbol)

        if SIMULATION_MODE:
            # Modo simulación: genera precios aleatorios cercanos
            price = round(random.uniform(0.95, 1.05), 4)
            logger.info(f"💬 [SIM] Precio simulado {normalized}: {price}")
            return price

        base_url = "https://api-testnet.bybit.com" if BYBIT_TESTNET else "https://api.bybit.com"
        endpoint = f"/v5/market/tickers?category=linear&symbol={normalized}"

        response = requests.get(base_url + endpoint, timeout=10)
        data = response.json()

        if "result" in data and "list" in data["result"] and len(data["result"]["list"]) > 0:
            last_price = float(data["result"]["list"][0]["lastPrice"])
            logger.info(f"💰 Precio actual {normalized}: {last_price}")
            return last_price

        logger.warning(f"⚠️ No se encontró precio para {normalized}")
        return 0.0

    except Exception as e:
        logger.error(f"❌ Error obteniendo precio actual: {e}")
        return 0.0


# ================================================================
# 🕒 Formatear timestamp legible
# ================================================================
def format_timestamp(ts: float | str | None = None) -> str:
    """
    Devuelve un timestamp legible para logs y BD.
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
# ⏳ Función de espera segura (para retardos en bucles)
# ================================================================
def safe_sleep(seconds: float):
    """
    Pausa segura que respeta interrupciones manuales.
    """
    try:
        for _ in range(int(seconds)):
            time.sleep(1)
    except KeyboardInterrupt:
        logger.warning("🛑 Ejecución detenida durante pausa.")
    except Exception as e:
        logger.error(f"❌ Error en safe_sleep: {e}")


# ================================================================
# 🧮 Calcular porcentaje de diferencia
# ================================================================
def percent_diff(a: float, b: float) -> float:
    """
    Calcula la diferencia porcentual entre dos valores.
    """
    try:
        if a == 0:
            return 0.0
        return round(((b - a) / a) * 100, 2)
    except Exception as e:
        logger.error(f"❌ Error calculando diferencia porcentual: {e}")
        return 0.0


# ================================================================
# 🔄 Normalizar dirección (LONG / SHORT)
# ================================================================
def normalize_direction(direction: str) -> str:
    """
    Convierte la dirección a formato estándar ('long' o 'short').
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
# 🧮 Redondeo seguro
# ================================================================
def safe_round(value: float, decimals: int = 4) -> float:
    """
    Redondea un valor de forma segura, evitando errores de tipo.
    """
    try:
        return round(float(value), decimals)
    except Exception:
        return 0.0
