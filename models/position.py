"""
models/position.py
-------------------
Modelo estándar de una posición abierta en Bybit.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionModel:
    symbol: str
    direction: str       # "long" o "short"
    entry_price: float
    size: float
    leverage: int
    pnl_pct: float
    pnl_usd: float
    mark_price: float
    timestamp: str = ""
