# ============================================================
# technical_brain_unified.py
# Motor técnico unificado – versión estable 2025-12
# Estructura: snapshot / smart_entry / final_decision
# ============================================================

import logging
import numpy as np

from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot
from services.technical_engine import trend_system_final
trends = trend_system_final.analyze_trend_core(snapshot, direction_hint)
from services.technical_engine.smart_entry_validator import evaluate_entry_smart
from services.technical_engine.smart_divergences import detect_smart_divergences

logger = logging.getLogger("technical_brain_unified")


# ============================================================
# RUN UNIFIED ANALYSIS
# ============================================================

def run_unified_analysis(
    symbol: str,
    direction_hint: str,
    entry_price: float | None = None,
    roi: float | None = None,
    loss_pct: float | None = None,
    context: str = ""
):
    """
    Motor técnico principal. Ensambla:
      ✔ snapshot multi–TF
      ✔ divergencias inteligentes
      ✔ smart entry
      ✔ final decision
    Devuelve: snapshot / smart_entry / decision
    """

    try:
        # =====================================================
        # 1) Tomar snapshot multi-temporalidad
        # =====================================================
        snapshot = get_multi_tf_snapshot(symbol)

        tf_snapshot = snapshot.get("timeframes", {})
        df_main = snapshot.get("df_main")

        # Ayuda para módulos siguientes
        main_status = snapshot.get("status", "unknown")
        if main_status != "ok":
            return {
                "symbol": symbol,
                "direction_hint": direction_hint,
                "snapshot": snapshot,
                "smart_entry": {
                    "entry_allowed": False,
                    "entry_mode": "no_data",
                    "entry_reasons": ["No hay datos OHLCV suficientes"]
                },
                "decision": {
                    "allowed": False,
                    "decision": "wait",
                    "decision_reasons": ["No hay datos suficientes en TF principales"],
                    "current_price": None,
                    "confidence": 0.0
                }
            }

        # =====================================================
        # 2) Calcular tendencias (major, overall, smart bias)
        # =====================================================
        trends = analyze_trend_core(snapshot, direction_hint)

        # =====================================================
        # 3) Divergencias inteligentes RSI / MACD
        # =====================================================
        divs = detect_smart_divergences(df_main)

        # =====================================================
        # 4) Smart entry (permite entrar sí/no)
        # =====================================================
        entry_eval = evaluate_entry_smart(
            df=df_main,
            direction_hint=direction_hint,
            major_trend=trends["major_trend"],
            overall_trend=trends["overall_trend"],
            divergences=divs
        )

        # =====================================================
        # 5) Cálculo de score general
        # =====================================================
        tech_score = entry_eval.get("entry_score", 0)
        grade = entry_eval.get("entry_grade", "D")

        match_ratio = trends.get("match_ratio", 0.0)

        # =====================================================
        # 6) DECISIÓN FINAL
        # =====================================================
        decision = entry_eval.get("entry_mode", "wait")
        reasons = entry_eval.get("entry_reasons", [])

        final_decision = {
            "allowed": entry_eval.get("entry_allowed", False),
            "decision": decision,
            "decision_reasons": reasons,
            "current_price": None,
            "confidence": float(match_ratio) / 100.0
        }

        # Guardar el precio actual
        try:
            if df_main is not None:
                final_decision["current_price"] = float(df_main.iloc[-1]["close"])
        except Exception:
            final_decision["current_price"] = None

        # =====================================================
        # 7) Bloque de retorno unificado (nuevo)
        # =====================================================
        return {
            "symbol": symbol,
            "direction_hint": direction_hint,

            # SNAPSHOT
            "snapshot": {
                "context": context,
                "timeframes": tf_snapshot,
                "major_trend": trends["major_trend"],
                "overall_trend": trends["overall_trend"],
                "smart_bias": trends["smart_bias"],
                "match_ratio": match_ratio,
                "technical_score": tech_score,
                "grade": grade,
            },

            # SMART ENTRY
            "smart_entry": entry_eval,

            # DECISIÓN FINAL
            "decision": final_decision,

            # Divergencias integradas
            "divergences": divs,
        }

    except Exception as e:
        logger.error(f"❌ Error en run_unified_analysis: {e}")

        return {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "snapshot": {"error": str(e)},
            "smart_entry": {"entry_allowed": False},
            "decision": {
                "allowed": False,
                "decision": "error",
                "decision_reasons": [str(e)],
                "current_price": None,
                "confidence": 0.0
            },
            "divergences": []
        }
