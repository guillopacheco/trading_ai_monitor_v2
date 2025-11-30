"""
controllers/positions_controller.py
-----------------------------------
Controlador de monitoreo de posiciones abiertas.

Flujo:
    scheduler_service → check_positions()
        → bybit_service.get_open_positions()
        → signal_engine.analyze_open_position_signal()
        → db.add_position_log()
        → telegram.send_message()  (si hay reversión)
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

# ============================================================
# 🔹 IMPORTS — sin ciclos
# ============================================================

from core.signal_engine import analyze_open_position_signal
import services.bybit_service as bybit_service
import services.db_service as db
from utils.helpers import now_ts

logger = logging.getLogger("positions_controller")


# ============================================================
# 🔹 Normalizadores
# ============================================================

def _normalize_direction(pos: Dict[str, Any]) -> str:
    """
    Interpreta la dirección (long/short) desde varias claves posibles.
    """
    for key in ("side", "positionSide", "direction"):
        v = pos.get(key)
        if isinstance(v, str):
            low = v.lower()
            if low.startswith(("b", "l")):
                return "long"
            if low.startswith(("s", "sh")):
                return "short"
    return "long"


def _extract_symbol(pos: Dict[str, Any]) -> Optional[str]:
    """
    Busca múltiples claves típicas de Bybit.
    """
    for key in ("symbol", "symbolName", "ticker"):
        v = pos.get(key)
        if isinstance(v, str) and v:
            return v.replace("/", "").upper()
    return None


def _extract_pnl_pct(pos: Dict[str, Any]) -> Optional[float]:
    """
    Extrae PnL % desde varias posibles claves.
    """
    for key in ("unrealisedPnlPct", "pnl_pct", "pnlPercent"):
        v = pos.get(key)
        if v in (None, "", "None"):
            continue
        try:
            return float(v)
        except Exception:
            continue
    return None


def _save_log(symbol: str, direction: str, pnl: float) -> None:
    """
    Guarda un registro en DB.
    """
    try:
        db.add_position_log(symbol, direction, pnl, now_ts())
    except Exception as e:
        logger.error(f"⚠️ Error guardando log de posición para {symbol}: {e}")


# ============================================================
# 🔹 FUNCIÓN PRINCIPAL
# ============================================================

async def check_positions() -> None:
    """
    Revisa posiciones abiertas mediante bybit_service y aplica Motor A+.
    """
    try:
        open_positions: List[Dict[str, Any]] = bybit_service.get_open_positions()
    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones de Bybit: {e}")
        return

    if not open_positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    # Import local para evitar ciclo telegram ↔ controller
    try:
        from services.telegram_service import send_message
    except Exception:
        send_message = None

    for pos in open_positions:
        symbol = _extract_symbol(pos)
        if not symbol:
            logger.warning(f"⚠️ Posición sin símbolo válido: {pos}")
            continue

        direction = _normalize_direction(pos)
        pnl_pct = _extract_pnl_pct(pos)

        logger.info(f"🔍 Analizando posición: {symbol} ({direction}), PnL={pnl_pct}%")
        _save_log(symbol, direction, pnl_pct or 0.0)

        # Motor A+
        try:
            result = await analyze_open_position_signal(
                symbol=symbol,
                direction=direction,
                pnl_pct=pnl_pct
            )
        except Exception as e:
            logger.exception(f"❌ Error analizando {symbol}: {e}")
            continue

        if not result.get("ok", False):
            logger.info(f"ℹ️ Motor A+ devolvió análisis incompleto para {symbol}.")
            continue

        if result.get("reversal", False):
            logger.warning(f"🚨 Reversión detectada para {symbol}")
            if send_message and result.get("text"):
                try:
                    await send_message(result["text"])
                except Exception as e:
                    logger.error(f"❌ Error enviando alerta Telegram: {e}")
        else:
            logger.info(f"✔ Sin reversión detectada para {symbol}")
