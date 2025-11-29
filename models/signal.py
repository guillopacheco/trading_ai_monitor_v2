"""
models/signal.py
----------------
Modelo de datos para una señal de trading.
Compatible con la arquitectura v2.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Signal:
    id: Optional[int]
    symbol: str
    direction: str
    entry: float
    tp_list: List[float]
    sl: float
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
