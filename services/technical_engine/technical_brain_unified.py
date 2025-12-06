# ============================================================
# technical_brain_unified.py
# Motor técnico unificado – versión estable 2025-12
# ============================================================

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot
from services.technical_engine.smart_entry_validator import evaluate_entry
from services.technical_engine.smart_divergences import detect_smart_divergences
from services.technical_engine import trend_system_final

logger = logging.getLogger("technical_brain_unified")


# ============================================================
# RUN UNIFIED ANALYSIS
# ============================================================

def run_unified_analysis(
    symbol: str,
    direction_hint: str,
    entry_price: Optional[float] = None,
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
    context: str = "",
) -> Dict[str, Any]:
    """
    Motor técnico principal. Ensambla:
      ✔ snapshot multi–TF
      ✔ tendencias principales (trend_system_final)
      ✔ divergencias inteligentes
      ✔ smart entry
      ✔ decisión final
    """

    try:
        # =====================================================
        # 1) Tomar snapshot multi-temporalidad
        # =====================================================
        snapshot = get_multi_tf_snapshot(symbol)

        tf_snapshot = snapshot.get("timeframes") or []
        df_main = snapshot.get("df_main")

        if snapshot.get("status") != "ok" or df_main is None:
            return {
                "symbol": symbol,
                "direction_hint": direction_hint,
                "snapshot": snapshot,
                "smart_entry": {
                    "entry_allowed": False,
                    "entry_mode": "no_data",
                    "entry_reasons": ["No hay datos OHLCV suficientes"],
                    "entry_score": 0.0,
                    "entry_grade": "D",
                },
                "decision": {
                    "allowed": False,
                    "decision": "wait",
                    "decision_reasons": ["No hay datos suficientes"],
                    "current_price": None,
                    "confidence": 0.0,
                },
                "divergences": [],
            }

        # =====================================================
        # 2) Calcular tendencias con trend_system_final
        #    (se trabaja DIRECTAMENTE sobre el snapshot)
        # =====================================================
        snapshot["direction_hint"] = direction_hint  # 🔥 agregar esto

        trends = trend_system_final.analyze_trend_core(
            snapshot,
            direction=direction_hint,
            context=context,
            roi=roi,
            loss_pct=loss_pct,
        )

        major_trend = trends.get("major_trend")
        overall_trend = trends.get("overall_trend", major_trend)
        smart_bias_label = trends.get("smart_bias")
        smart_bias_code = trends.get("smart_bias_code")
        match_ratio = trends.get("match_ratio", 0.0)
        tech_score = trends.get("technical_score", match_ratio)
        grade = trends.get("grade", "D")

        # Para compatibilidad con otros módulos que usan *_code / *_label
        major_trend_label = trends.get("major_trend_label")
        overall_trend_label = trends.get("overall_trend_label")

        # =====================================================
        # 3) Divergencias inteligentes RSI/MACD
        #    (se apoyan en df_main ya enriquecido con indicadores)
        # =====================================================
        divergences = detect_smart_divergences(df_main)

        # =====================================================
        # 4) Smart entry
        # =====================================================
        entry_eval = evaluate_entry(
            df=df_main,
            direction_hint=direction_hint,
            major_trend=major_trend,
            overall_trend=overall_trend,
            divergences=divergences,
        )

        entry_allowed = bool(entry_eval.get("entry_allowed", False))
        entry_mode = entry_eval.get("entry_mode", "wait")
        entry_reasons = entry_eval.get("entry_reasons", [])

        # =====================================================
        # 5) Decisión final
        # =====================================================
        decision = {
            "allowed": entry_allowed,
            "decision": entry_mode,
            "decision_reasons": entry_reasons,
            "current_price": None,
            "confidence": float(match_ratio) / 100.0,
        }

        # Precio actual — último cierre disponible
        try:
            decision["current_price"] = float(df_main.iloc[-1]["close"])
        except Exception:
            decision["current_price"] = None

            # 🔧 Inyectar tendencia mayor a todos los TF si falta
        if major_trend:
            snapshot["major_trend_code"] = major_trend
            snapshot["major_trend_label"] = major_trend_label

            for tf in tf_snapshot:
                if not tf.get("trend_code"):
                    tf["trend_code"] = major_trend

        # =====================================================
        # 6) Resultado final unificado
        # =====================================================
        return {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "snapshot": {
                "context": context,
                "timeframes": tf_snapshot,
                "major_trend": major_trend,
                "major_trend_code": major_trend,  # código simple bull/bear/sideways
                "major_trend_label": major_trend_label,
                "overall_trend": overall_trend,
                "overall_trend_label": overall_trend_label,
                "smart_bias": smart_bias_label,
                "smart_bias_code": smart_bias_code,
                "match_ratio": match_ratio,
                "technical_score": tech_score,
                "grade": grade,
                # 🔹 Divergencias inteligentes integradas al snapshot
                "divergences": divergences,
            },
            "smart_entry": entry_eval,
            "decision": decision,
            "divergences": divergences,
        }

    except Exception as e:
        logger.error(f"❌ Error en run_unified_analysis: {e}")

        return {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "snapshot": {"error": str(e)},
            "smart_entry": {
                "entry_allowed": False,
                "entry_mode": "error",
                "entry_reasons": [str(e)],
                "entry_score": 0.0,
                "entry_grade": "D",
            },
            "decision": {
                "allowed": False,
                "decision": "error",
                "decision_reasons": [str(e)],
                "current_price": None,
                "confidence": 0.0,
            },
            "divergences": [],
        }
