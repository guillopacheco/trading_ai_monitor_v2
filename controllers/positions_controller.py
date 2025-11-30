"""
controllers/positions_controller.py
-----------------------------------
Controlador de monitoreo de posiciones abiertas.

Flujo:
    scheduler_service.positions_loop()
        → check_positions()
        → services.bybit_service.get_open_positions()
        → core.signal_engine.analyze_open_position_signal()
        → db_service.add_position_log() (opcional)
        → telegram_service.send_message() (alertas de reversión)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# Motor A+
try:
    from core.signal_engine import analyze_open_position_signal
except Exception:
    from signal_engine import analyze_open_position_signal  # type: ignore

# Servicios
try:
    import services.bybit_service as bybit_service  # type: ignore
except Exception:  # pragma: no cover
    bybit_service = None  # type: ignore

try:
    import services.db_service as db_service  # type: ignore
except Exception:  # pragma: no cover
    db_service = None  # type: ignore

try:
    from utils.helpers import now_ts
except Exception:
    from datetime import datetime

    def now_ts() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")


logger = logging.getLogger("positions_controller")


# ============================================================
# 🔹 Utilidades internas
# ============================================================

def _normalize_direction_from_position(pos: Dict[str, Any]) -> str:
    """
    Interpreta la dirección de la posición a partir del dict de Bybit.

    Intenta usar, en orden:
        - pos["side"]
        - pos["positionSide"]
        - pos["direction"]

    Devuelve "long" o "short".
    """
    for key in ("side", "positionSide", "direction"):
        v = pos.get(key)
        if isinstance(v, str):
            v_low = v.lower()
            if v_low.startswith(("b", "l")):
                return "long"
            if v_low.startswith(("s", "sh")):
                return "short"
    # Por defecto
    return "long"


def _get_symbol_from_position(pos: Dict[str, Any]) -> Optional[str]:
    """
    Extrae el símbolo de la posición.
    """
    for key in ("symbol", "symbolName", "ticker"):
        v = pos.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def _get_pnl_pct_from_position(pos: Dict[str, Any]) -> Optional[float]:
    """
    Intenta obtener el PnL % de la posición.
    Busca claves típicas de Bybit.
    """
    for key in ("unrealisedPnlPct", "pnl_pct", "pnlPercent"):
        v = pos.get(key)
        if v is None:
            continue
        try:
            return float(v)
        except Exception:
            continue
    return None


def _log_position(symbol: str, direction: str, pnl_pct: Optional[float]) -> None:
    """
    Guarda log en DB si está disponible.
    """
    if db_service is None or not hasattr(db_service, "add_position_log"):
        return

    try:
        db_service.add_position_log(symbol, direction, pnl_pct or 0.0, now_ts())  # type: ignore
    except Exception as e:
        logger.error(f"⚠️ No se pudo registrar log de posición para {symbol}: {e}")


# ============================================================
# 🔹 FUNCIÓN PÚBLICA: revisar posiciones
# ============================================================

async def check_positions() -> None:
    """
    Revisa las posiciones abiertas en Bybit y detecta posibles reversiones.
    Llamada periódicamente por services/scheduler_service.py
    """
    if bybit_service is None or not hasattr(bybit_service, "get_open_positions"):
        logger.warning("⚠️ bybit_service.get_open_positions no disponible.")
        return

    try:
        positions: List[Dict[str, Any]] = bybit_service.get_open_positions()  # type: ignore
    except Exception as e:
        logger.error(f"❌ Error obteniendo posiciones abiertas: {e}")
        return

    if not positions:
        logger.info("📭 No hay posiciones abiertas.")
        return

    # Import local para evitar cualquier posible ciclo con telegram_service
    try:
        from services.telegram_service import send_message  # type: ignore
    except Exception:
        send_message = None  # type: ignore

    for pos in positions:
        symbol = _get_symbol_from_position(pos)
        if not symbol:
            logger.warning(f"⚠️ Posición sin símbolo válido: {pos}")
            continue

        direction = _normalize_direction_from_position(pos)
        pnl_pct = _get_pnl_pct_from_position(pos)

        logger.info(f"🔍 Analizando posición: {symbol} ({direction}), PnL={pnl_pct}%")

        _log_position(symbol, direction, pnl_pct)

        try:
            analysis = await analyze_open_position_signal(symbol, direction)
        except Exception as e:
            logger.exception(f"❌ Error en analyze_open_position_signal para {symbol}: {e}")
            continue

        if not analysis.get("ok", False):
            logger.info(f"ℹ️ Análisis incompleto para posición {symbol}.")
            continue

        reversal = analysis.get("reversal", False)
        text = analysis.get("text")

        if reversal:
            logger.warning(f"🚨 Reversión detectada en {symbol}.")
            if send_message is not None and text:
                try:
                    await send_message(text)
                except Exception as e:
                    logger.error(f"❌ Error enviando alerta de reversión a Telegram: {e}")
        else:
            logger.info(f"✔ Sin reversión detectada para {symbol}.")
