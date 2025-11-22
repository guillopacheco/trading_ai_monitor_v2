"""
motor_wrapper.py — Capa estable sobre el motor técnico
-------------------------------------------------------

Objetivo:
- Evitar que cambios internos en trend_system_final rompan el resto de la app.
- Dar un único punto de entrada para:
    * Señales nuevas (canal VIP)
    * Reactivaciones automáticas
    * Monitoreo de reversiones

En esta PRIMERA versión el wrapper es casi transparente:
- Delegamos en trend_system_final.analyze_and_format / analyze_trend_core.
- Normalizamos el diccionario de salida para que siempre tenga las claves
  que usan otros módulos: match_ratio, major_trend, smart_bias, divergences, etc.

Más adelante:
- Podremos reforzar el peso de divergencias en 4h/1h.
- Podremos cambiar el “modo” (aggressive/balanced/conservative) sin tocar
  telegram_reader, signal_reactivation_sync ni position_reversal_monitor.
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

    # Campos básicos
    result: Dict[str, Any] = {
        "symbol": raw.get("symbol", symbol),
        "direction_hint": direction_hint,
        "timeframes": raw.get("timeframes"),          # puede ser dict o None
        "major_trend": raw.get("major_trend"),
        "overall_trend": raw.get("overall_trend"),
        "match_ratio": float(raw.get("match_ratio", 0.0) or 0.0),
        "confidence": float(raw.get("confidence", 0.0) or 0.0),
        "confidence_label": raw.get("confidence_label"),
        "smart_bias": raw.get("smart_bias"),
        "allowed": bool(raw.get("allowed", True)),
    }

    # Divergencias agregadas
    divs = raw.get("divergences") or raw.get("divergence_summary") or {}
    if not isinstance(divs, dict):
        divs = {}

    result["divergences"] = {
        "RSI": divs.get("RSI") or divs.get("rsi") or "",
        "MACD": divs.get("MACD") or divs.get("macd") or "",
    }

    # Por compatibilidad, si major_trend no está, usamos overall_trend
    if not result["major_trend"] and result["overall_trend"]:
        result["major_trend"] = result["overall_trend"]

    return result


# ================================================================
# 📌 API pública — usar SIEMPRE estas funciones
# ================================================================
def analyze_for_signal(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Análisis principal cuando llega una señal nueva del canal VIP.

    Devuelve:
    - result: dict normalizado (major_trend, match_ratio, divergences, etc.)
    - report: cadena de texto lista para enviar a Telegram.
    """
    try:
        raw_result, report = _legacy_analyze_and_format(
            symbol=symbol,
            direction_hint=direction_hint,
        )
    except Exception as e:
        logger.error(f"❌ Error en analyze_for_signal({symbol}): {e}")
        # Fallback muy defensivo
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

    Por ahora delega en analyze_for_signal (mismo análisis),
    pero si en el futuro queremos reglas específicas para reactivación,
    solo se cambia aquí.
    """
    return analyze_for_signal(symbol, direction_hint=direction_hint)


def analyze_for_reversal(
    symbol: str,
    direction_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Análisis “crudo” para el monitor de reversiones de posiciones.

    Devuelve SOLO el dict normalizado (sin texto formateado),
    porque position_reversal_monitor construye su propio mensaje.
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
    Reexpone los thresholds del motor antiguo, por compatibilidad.
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
