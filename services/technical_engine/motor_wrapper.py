"""
motor_wrapper.py — versión UNIFICADA 2025-11
---------------------------------------------
Wrapper oficial del sistema.
Toda la app (Telegram, DB, reactivación, reversión, monitoreo) llama aquí.

Esta versión ya NO usa múltiples motores.
Únicamente llama a trend_system_final.analyze_trend_core(),
que está respaldado por technical_brain_unified.py
y el motor técnico unificado technical_engine.py.

La API pública NO cambia.
---------------------------------------------
"""
import logging

from services.technical_engine.trend_system_final import analyze_trend_core
from services.technical_engine.technical_engine import format_analysis

logger = logging.getLogger("motor_wrapper")

# ============================================================
# 🧠 Normalización (compatibilidad histórica)
# ============================================================

def _normalize_result(result: dict):
    """
    Garantiza que el diccionario tenga siempre los campos esperados
    por operaciones, reactivación, reversión y Telegram.
    """
    if not isinstance(result, dict):
        return {}

    normalized = {
        "symbol": result.get("symbol"),
        "direction_hint": result.get("direction_hint"),

        "major_trend": result.get("major_trend", "neutral"),
        "overall_trend": result.get("overall_trend", "neutral"),

        "match_ratio": float(result.get("match_ratio", 0)),
        "technical_score": float(result.get("technical_score", 0)),
        "grade": result.get("grade", "D"),
        "confidence": float(result.get("confidence", 0)),
        "confidence_label": result.get("confidence_label", "low"),
        "smart_bias": result.get("smart_bias", "neutral"),
        "divergences": result.get("divergences", {}),

        "allowed": result.get("allowed", False),
        "decision": result.get("decision", "unknown"),
        "decision_reasons": result.get("decision_reasons", []),

        # Smart entry integrado
        "entry_score": result.get("entry_score", 0),
        "entry_grade": result.get("entry_grade", "D"),
        "entry_mode": result.get("entry_mode", "block"),
        "entry_allowed": result.get("entry_allowed", False),
        "entry_reasons": result.get("entry_reasons", []),

        # Bloque debug
        "debug": result.get("debug", {})
    }

    return normalized


# ============================================================
# 📈 Análisis para señales nuevas
# ============================================================

def analyze_for_signal(symbol: str, direction: str):
    """
    Usado por telegram_reader.
    """
    try:
        result = analyze_trend_core(symbol, direction, context="entry")
        return _normalize_result(result)
    except Exception as e:
        logger.error(f"❌ Error analyze_for_signal: {e}")
        return {"allowed": False, "decision": "error"}


# ============================================================
# 🔁 Análisis para reactivación
# ============================================================

def analyze_for_reactivation(symbol: str, direction: str):
    """
    Usado por signal_reactivation_sync.py
    """
    try:
        result = analyze_trend_core(symbol, direction, context="reactivation")
        return _normalize_result(result)
    except Exception as e:
        logger.error(f"❌ Error analyze_for_reactivation: {e}")
        return {"allowed": False, "decision": "error"}


# ============================================================
# 🔄 Análisis para reversión (-50% / riesgo severo)
# ============================================================

def analyze_for_reversal(symbol: str, direction: str):
    """
    Usado por position_reversal_monitor.py
    """
    try:
        result = analyze_trend_core(symbol, direction, context="reversal")
        return _normalize_result(result)
    except Exception as e:
        logger.error(f"❌ Error analyze_for_reversal: {e}")
        return {"allowed": False, "decision": "error"}


# ============================================================
# ⚙️ Thresholds públicos
# ============================================================

def get_thresholds():
    return get_thresholds_public()
