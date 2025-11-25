"""
motor_wrapper.py — Capa estable sobre el motor técnico
-------------------------------------------------------

Objetivo:
- Evitar que cambios internos en trend_system_final rompan el resto de la app.
- Dar un único punto de entrada para:
    * Señales nuevas (canal VIP)
    * Reactivaciones automáticas
    * Monitoreo de reversiones

En esta versión:
- Normaliza la salida del motor técnico (trend_system_final)
- Integra Smart Entry dentro de _normalize_result()
- No tiene bloques inconsistentes ni referencias a “debug”
"""

from __future__ import annotations

import logging
from typing import Tuple, Dict, Any, Optional

# Motor técnico actual
from trend_system_final import (
    analyze_trend_core as _legacy_core,
    analyze_and_format as _legacy_analyze_and_format,
    _get_thresholds,
)

# Smart Entry integrado en normalize_result
from smart_entry_validator import evaluate_entry as _evaluate_entry

logger = logging.getLogger("motor_wrapper")


# ================================================================
# 🔧 Normalizador de resultados
# ================================================================
def _normalize_result(
    raw: Dict[str, Any],
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Garantiza que el resultado siempre tenga las mismas claves
    que usan otros módulos (aunque trend_system_final cambie por dentro).
    """

    direction_hint = (direction_hint or raw.get("direction_hint") or "").lower()

    result: Dict[str, Any] = {
        "symbol": raw.get("symbol", symbol),
        "direction_hint": direction_hint,
        "timeframes": raw.get("timeframes"),
        "major_trend": raw.get("major_trend"),
        "overall_trend": raw.get("overall_trend"),
        "match_ratio": float(raw.get("match_ratio", 0.0) or 0.0),
        "confidence": float(raw.get("confidence", 0.0) or 0.0),
        "confidence_label": raw.get("confidence_label"),
        "smart_bias": raw.get("smart_bias"),
        "allowed": bool(raw.get("allowed", True)),
    }

    # Divergencias
    divs = raw.get("divergences") or raw.get("divergence_summary") or {}
    if not isinstance(divs, dict):
        divs = {}

    result["divergences"] = {
        "RSI": divs.get("RSI") or divs.get("rsi") or "",
        "MACD": divs.get("MACD") or divs.get("macd") or "",
    }

    # Fallback
    if not result["major_trend"] and result["overall_trend"]:
        result["major_trend"] = result["overall_trend"]

    # ============================================================
    # 🧠 Smart Entry integrado
    # ============================================================
    try:
        debug = raw.get("debug") or {}
        snapshot = debug.get("raw_snapshot")
        if isinstance(snapshot, dict):
            entry_info = _evaluate_entry(symbol, direction_hint, snapshot)

            result["entry_score"] = entry_info.get("entry_score")
            result["entry_grade"] = entry_info.get("entry_grade")
            result["entry_mode"] = entry_info.get("entry_mode")
            result["entry_allowed"] = bool(entry_info.get("entry_allowed", True))
            result["entry_reasons"] = entry_info.get("entry_reasons", [])

            if not result["entry_allowed"]:
                result["allowed"] = False

    except Exception as e:
        logger.error(f"⚠️ Error en Smart Entry para {symbol}: {e}")

    return result


# ================================================================
# 📌 API pública — usar SIEMPRE estas funciones
# ================================================================
def analyze_for_signal(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Análisis principal utilizado cuando llega una señal nueva del canal VIP.
    """
    try:
        raw_result, report = _legacy_analyze_and_format(
            symbol=symbol,
            direction_hint=direction_hint,
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_for_signal({symbol}): {e}")
        raw_result = {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "major_trend": None,
            "overall_trend": None,
            "match_ratio": 0.0,
            "confidence": 0.0,
            "confidence_label": "low",
            "smart_bias": None,
            "divergences": {},
            "allowed": False,
        }
        report = (
            f"❌ Error interno al analizar {symbol}. "
            f"Revisa los logs del servidor."
        )

    result = _normalize_result(raw_result, symbol, direction_hint)
    return result, report


def analyze_for_reactivation(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Análisis usado por el ciclo de reactivación automática.
    """
    return analyze_for_signal(symbol, direction_hint=direction_hint)


def analyze_for_reversal(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Análisis crudo utilizado por position_reversal_monitor.
    """
    try:
        raw = _legacy_core(symbol, direction_hint=direction_hint)
    except Exception as e:
        logger.error(f"❌ Error en analyze_for_reversal({symbol}): {e}")
        raw = {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "major_trend": None,
            "overall_trend": None,
            "match_ratio": 0.0,
            "confidence": 0.0,
            "confidence_label": "low",
            "smart_bias": None,
            "divergences": {},
            "allowed": False,
        }

    return _normalize_result(raw, symbol, direction_hint)


def get_thresholds() -> Dict[str, float]:
    """
    Reexpone thresholds del motor antiguo.
    """
    try:
        return _get_thresholds()
    except Exception as e:
        logger.error(f"❌ Error obteniendo thresholds: {e}")
        return {
            "entry": 60.0,
            "reactivation": 75.0,
            "internal": 55.0,
        }
