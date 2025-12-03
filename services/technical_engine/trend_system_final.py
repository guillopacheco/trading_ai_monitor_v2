import logging
from typing import Optional

# ✅ IMPORT CORRECTO (solo este)
from services.technical_engine.technical_brain_unified import run_unified_analysis

logger = logging.getLogger("trend_system_final")

# ============================================================
# THRESHOLDS Y PESOS — DEFINIDOS LOCALMENTE
# ============================================================

def get_thresholds():
    return {
        "grade_A": 85,
        "grade_B": 70,
        "grade_C": 55,
    }

def get_bias_weight():
    return {
        "strong": 1.0,
        "moderate": 0.7,
        "weak": 0.4,
    }

def get_score_weight():
    return {
        "trend": 0.5,
        "momentum": 0.3,
        "divergence": 0.2,
    }


# ============================================================
# 📌 FUNCIÓN BASE
# ============================================================

def analyze_trend_core(
    symbol: str,
    direction: Optional[str] = None,
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
):
    try:
        result = run_unified_analysis(
            symbol,
            direction,
            context=context,
            roi=roi,
            loss_pct=loss_pct,
        )
        return result

    except Exception as e:
        logger.error(f"❌ Error en analyze_trend_core: {e}")
        return {
            "symbol": symbol,
            "direction_hint": direction,
            "allowed": False,
            "decision": "error",
            "decision_reasons": [str(e)],
            "roi": roi,
            "loss_pct": loss_pct,
        }


# ============================================================
# ⚙️ API PÚBLICA (para reactivadores, reversales, telegram)
# ============================================================

def _get_thresholds():
    return get_thresholds()

get_thresholds_public = _get_thresholds
