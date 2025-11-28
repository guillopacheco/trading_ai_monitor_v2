"""
models/reactivation.py
----------------------
Modelo para representar el resultado de una reactivación de señal.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class ReactivationResult:
    signal_id: int
    symbol: str
    direction: str
    match_ratio: float
    grade: str
    decision: str
    triggered: bool
    details: str = ""
