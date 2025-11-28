"""
models/analysis.py
-------------------
Modelo estándar de los resultados técnicos generados por signal_engine.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class AnalysisResult:
    symbol: str
    direction: str
    match_ratio: float
    grade: str
    decision: str       # enter / wait / skip / reversal-risk / close / keep / reverse
    details: str = ""   # texto para logs o notificación
    debug: Optional[Dict] = None   # datos internos (opcional para DEBUG_MODE)
