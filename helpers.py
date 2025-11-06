"""
Funciones auxiliares para cálculos de riesgo, ROI y operaciones
"""
import logging
import random

logger = logging.getLogger("helpers")

# ================================================================
# ⚙️ Configuración de apalancamiento y riesgo
# ================================================================
LEVERAGE = 20
RISK_PER_TRADE = 0.05
MAX_LEVERAGE = 20
MAX_POSITION_SIZE = 0.1
ACCOUNT_BALANCE = 1000

# ================================================================
# 💹 Umbrales ROI (gestión de pérdidas y ganancias)
# ================================================================
ROI_REVERSION_THRESHOLD = -30
ROI_DYNAMIC_STOP_THRESHOLD = 60
ROI_TAKE_PROFIT_THRESHOLD = 100
ROI_PARTIAL_CLOSE_PERCENT = 70

# ================================================================
# 💰 Cálculos de ROI y precio actual
# ================================================================
def calculate_roi(entry_price: float, current_price: float, direction: str, leverage: int) -> float:
    try:
        pnl = ((current_price - entry_price) / entry_price) * 100
        if direction.lower() == "short":
            pnl *= -1
        roi = pnl * leverage
        return round(roi, 2)
    except Exception as e:
        logger.error(f"Error calculando ROI: {e}")
        return 0.0

def get_current_price(symbol: str) -> float:
    # ⚠️ Este valor se obtiene de Bybit o se simula según el modo
    try:
        # En modo simulación, retorna un valor aleatorio entre ±2%
        return round(random.uniform(0.98, 1.02), 4)
    except Exception as e:
        logger.error(f"Error obteniendo precio actual para {symbol}: {e}")
        return 0.0
