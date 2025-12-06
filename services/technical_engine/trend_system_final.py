import logging
from typing import Optional, Dict, Any

# ✅ ÚNICO MOTOR TÉCNICO REAL
# En vez de usar technical_brain_unified.run_unified_analysis,
# delegamos TODO al motor unificado de technical_engine.analyze.
from services.technical_engine.technical_engine import analyze as core_analyze

logger = logging.getLogger("trend_system_final")


# ============================================================
# THRESHOLDS Y PESOS — DEFINIDOS LOCALMENTE
# (Se mantienen por compatibilidad, pero la lógica fina
#  de score y decisión vive en technical_engine)
# ============================================================

def get_thresholds() -> Dict[str, Any]:
    return {
        "grade_A": 85,
        "grade_B": 70,
        "grade_C": 55,
        "min_match_for_reactivation": 65,
        "min_score_for_reactivation": 60,
    }


# ============================================================
# 🎯 ENVOLTURA SOBRE EL MOTOR ÚNICO
# ============================================================

def analyze_trend_core(
    symbol: str,
    side: str,
    entry_price: Optional[float] = None,
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
    context: str = "entry",
) -> Dict[str, Any]:
    """Puerta de entrada *única* para el análisis técnico.

    IMPORTANTE:
    - Todos los servicios externos (reactivación, reversales,
      operación abierta, /analizar en Telegram) deben llamar SIEMPRE
      a esta función o a los helpers de motor_wrapper.
    - Internamente delega al motor unificado technical_engine.analyze.
    - `entry_price` hoy no se usa en el motor, pero se mantiene
      en la firma para compatibilidad hacia atrás.
    """
    logger.info(
        "➡️ [trend_system_final] Delegando análisis a technical_engine.analyze "
        "(%s, %s, context=%s, roi=%s, loss=%s)",
        symbol,
        side,
        context,
        roi,
        loss_pct,
    )

    try:
        # Motor único real
        result = core_analyze(
            symbol=symbol,
            side=side,
            context=context,
            loss_pct=loss_pct,
            roi=roi,
        )

        # Nos aseguramos de adjuntar siempre el símbolo y side
        result.setdefault("symbol", symbol)
        result.setdefault("direction_hint", side)

        return result

    except Exception as e:
        logger.exception("❌ Error en analyze_trend_core para %s: %s", symbol, e)
        return {
            "allowed": False,
            "decision": "wait",
            "decision_reasons": [str(e)],
            "symbol": symbol,
            "direction_hint": side,
            "technical_score": 0.0,
            "match_ratio": 0.0,
            "grade": "D",
            "confidence": 0.0,
            "context": context,
            "roi": roi,
            "loss_pct": loss_pct,
        }


# ============================================================
# ⚙️ API PÚBLICA (para otros módulos)
# ============================================================

def _get_thresholds() -> Dict[str, Any]:
    return get_thresholds()

# Alias de compatibilidad para otros módulos
get_thresholds_public = _get_thresholds
