"""
models/signal.py
----------------
Modelo estándar para representar una señal de trading.

Este modelo se utiliza en toda la app:
- signal_listener
- signal_controller
- db_service
- signal_engine
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SignalModel:
    id: Optional[int] = None   # asignado por la DB
    symbol: str = ""
    direction: str = ""        # long / short
    entry: Optional[float] = None
    tp_list: List[float] = field(default_factory=list)
    sl: Optional[float] = None
    leverage: Optional[int] = 20
    raw_text: str = ""

    # Estado interno
    status: str = "new"         # new / pending / active / ignored / done
    match_ratio: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
