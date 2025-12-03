"""
technical_brain_unified.py
------------------------------------------
Motor técnico unificado (2025-11)

Unifica:
✔ multi-TF
✔ match_ratio
✔ divergencias clásicas y smart
✔ smart_bias
✔ technical_score
✔ entrada inteligente (A–D + ok/warn/block)
✔ reactivación inteligente
✔ reversión (riesgo)
✔ coherencia de decisiones

Entrega siempre un único diccionario estándar.
------------------------------------------
"""

import logging
import pprint
from typing import Optional

from config import DEBUG_MODE, EMA_SHORT_PERIOD, EMA_MID_PERIOD, EMA_LONG_PERIOD
from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot
from services.technical_engine.smart_entry_validator import evaluate_entry
from services.technical_engine.smart_divergences import detect_smart_divergences
from services.technical_engine.indicators import *

logger = logging.getLogger("technical_brain_unified")

# ============================================================
# 🔢 Thresholds unificados
# ============================================================

THRESHOLDS = {
    "entry": {
        "min_match": 55,
        "min_score": 50,
    },
    "reactivation": {
        "min_match": 50,
        "min_score": 45,
    },
    # Uso interno genérico
    "internal": {
        "min_match": 45,
        "min_score": 40,
    },
    # Nuevo contexto para operaciones abiertas
    "operation": {
        "min_match": 45,
        "min_score": 40,
    },
}


def get_thresholds():
    """Exporta thresholds compatibles con motor_wrapper."""
    return {
        "entry": THRESHOLDS["entry"]["min_match"],
        "reactivation": THRESHOLDS["reactivation"]["min_match"],
        "internal": THRESHOLDS["internal"]["min_match"],
    }


# ============================================================
# 🎛️ Normalizadores
# ============================================================

def _trend_label(code):
    return {
        2: "bullish",
        1: "slightly-bullish",
        0: "neutral",
        -1: "slightly-bearish",
        -2: "bearish"
    }.get(code, "neutral")


def _confidence_label(c):
    if c >= 0.66:
        return "high"
    if c >= 0.33:
        return "medium"
    return "low"


def _debug_report(symbol, direction_hint, snapshot, entry, final):
    """
    Genera un reporte detallado del proceso técnico.
    Solo aparece si DEBUG_MODE = True.
    """
    logger.info("\n" + "=" * 70)
    logger.info(f"🟦 DEBUG REPORT — {symbol} ({direction_hint})")
    logger.info("=" * 70)

    # ---------- SNAPSHOT ----------
    logger.info("\n📌 SNAPSHOT MULTI-TF (raw):")
    try:
        logger.info(pprint.pformat(snapshot, indent=4, compact=False))
    except Exception:
        logger.info(str(snapshot))

    # ---------- SMART ENTRY ----------
    logger.info("\n🎯 SMART ENTRY:")
    try:
        logger.info(pprint.pformat(entry, indent=4))
    except Exception:
        logger.info(str(entry))

    # ---------- FINAL RESULT ----------
    logger.info("\n📘 FINAL DECISION:")
    try:
        logger.info(pprint.pformat(final, indent=4))
    except Exception:
        logger.info(str(final))

    logger.info("=" * 70 + "\n")


# ============================================================
# 🧠 Motor técnico unificado
# ============================================================

def run_unified_analysis(
    symbol: str,
    direction_hint: Optional[str] = None,
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
):
    """
    Motor técnico principal.
    Produce una estructura final consistente que usa toda la app.

    Parámetros extra:
    - roi: ROI con apalancamiento (porcentaje, ej -55.0)
    - loss_pct: pérdida sin apalancamiento (aprox), útil para lógica de riesgo.
    """

    try:
        # --------------------------------------------------------
        # 1) MULTI-TF SNAPSHOT  (core principal)
        # --------------------------------------------------------
        snapshot = get_multi_tf_snapshot(symbol, direction_hint)

        major_trend = _trend_label(snapshot.get("major_trend_code"))
        overall_trend = _trend_label(snapshot.get("overall_trend_code"))
        match_ratio = float(snapshot.get("match_ratio", 0))
        technical_score = float(snapshot.get("technical_score", 0))
        grade = snapshot.get("grade", "D")
        confidence = float(snapshot.get("confidence", 0))
        smart_bias = snapshot.get("smart_bias_code", "neutral")
        divergences = snapshot.get("divergences", {})

        timeframes = snapshot.get("timeframes", {})

        confidence_lbl = _confidence_label(confidence)

        # --------------------------------------------------------
        # 2) SMART ENTRY integrado (A–D, ok/warn/block)
        # --------------------------------------------------------
        entry = evaluate_entry(symbol, direction_hint, snapshot)

        entry_score = entry.get("entry_score", 0)
        entry_grade = entry.get("entry_grade", "D")
        entry_mode = entry.get("entry_mode", "block")
        entry_allowed = entry.get("entry_allowed", False)
        entry_reasons = entry.get("entry_reasons", [])

        # --------------------------------------------------------
        # 3) DECISIÓN PRINCIPAL (entrada / reactivación / reversión / operación)
        # --------------------------------------------------------
        decision = "wait"
        decision_reasons = []
        allowed = False
        risk_level = None  # solo se usa en contexto "operation"

        # Selección threshold según contexto
        ctx_thr = THRESHOLDS.get(context, THRESHOLDS["entry"])
        min_match = ctx_thr["min_match"]
        min_score = ctx_thr["min_score"]

        # ---------- A. LÓGICA PARA ENTRADA ----------
        if context == "entry":

            # Condición base para entrada
            if match_ratio >= min_match and technical_score >= min_score:
                allowed = True
                decision = "enter"
                decision_reasons.append(
                    f"Alineación suficiente: match={match_ratio:.1f} score={technical_score:.1f}"
                )
            else:
                allowed = False
                decision = "skip"
                decision_reasons.append(
                    f"Coincidencia insuficiente: match={match_ratio:.1f} score={technical_score:.1f}"
                )

            # ↓↓↓ Ajustes según divergencias / smart_bias
            if smart_bias.endswith("reversal") or "bearish" in str(divergences) or "bullish" in str(divergences):
                # Si está alineado fuerte, degradar a warn
                if allowed and entry_grade in ("A", "B"):
                    decision = "enter"
                    allowed = True
                    if entry_mode != "ok":
                        entry_mode = "warn"
                    decision_reasons.append("Divergencias leves o smart_bias de reversión")
                else:
                    # Si la estructura es débil → skip
                    allowed = False
                    decision = "skip"
                    decision_reasons.append("Reversión fuerte detectada en divergencias")

            # Bloqueo final si entry_mode="block"
            if entry_mode == "block":
                allowed = False
                decision = "skip"
                decision_reasons.append("Entrada bloqueada por Smart Entry")

        # ---------- B. REACTIVACIÓN ----------
        elif context == "reactivation":

            if match_ratio >= min_match and technical_score >= min_score:
                allowed = True
                decision = "reactivate"
                decision_reasons.append(
                    f"Condiciones favorables: match={match_ratio:.1f}, score={technical_score:.1f}"
                )
            else:
                # esperar
                decision = "wait"
                allowed = False
                decision_reasons.append(
                    f"Condiciones insuficientes para reactivar (match={match_ratio:.1f}, score={technical_score:.1f})"
                )

            # Penalización por divergencias duras en contra
            if "reversal" in smart_bias and (grade == "D" or entry_grade == "D"):
                allowed = False
                decision = "wait"
                decision_reasons.append("Reversión fuerte detectada → esperar")

        # ---------- C. OPERACIONES ABIERTAS (monitor de riesgo) ----------
        elif context == "operation":
            # ROI y pérdida sin apalancamiento
            # ROI suele venir en %, ej: -55.0
            base_loss = loss_pct
            if base_loss is None and roi is not None:
                # aproximación: pérdida sin apalancamiento ≈ roi / leverage
                # (ya viene calculado en operation_tracker, pero dejamos fallback)
                base_loss = roi

            # Clasificación gruesa del nivel de pérdida
            if base_loss is not None:
                if base_loss <= -70:
                    risk_level = "critical"
                elif base_loss <= -50:
                    risk_level = "high"
                elif base_loss <= -30:
                    risk_level = "medium"
                elif base_loss <= -20:
                    risk_level = "low"
                else:
                    risk_level = "very-low"

            decision = "hold"
            allowed = False

            # Beneficio alto: sugerir mantener salvo señales claras de giro
            if roi is not None and roi >= 30:
                decision_reasons.append("Beneficio elevado, sin necesidad de cierre inmediato.")

            # Si la pérdida es baja o muy baja → mantener, salvo reversión muy fuerte
            if risk_level in (None, "very-low", "low"):
                decision = "hold"
                allowed = False
                if risk_level is not None:
                    decision_reasons.append("Pérdida controlada, estructura no crítica.")

                if "reversal" in smart_bias and grade in ("C", "D"):
                    # Hay reversión potencial pero pérdida aún manejable
                    decision = "watch"
                    allowed = True
                    decision_reasons.append("Señales de reversión con pérdida moderada → vigilar de cerca.")

            # Pérdida media → vigilar activamente
            elif risk_level == "medium":
                decision = "watch"
                allowed = True
                decision_reasons.append("Pérdida moderada, requiere vigilancia activa.")

                # Si además la estructura técnica es floja
                if match_ratio < min_match or technical_score < min_score or grade == "D":
                    decision = "close"
                    decision_reasons.append(
                        "Pérdida moderada + estructura técnica débil → cerrar para proteger capital."
                    )

            # Pérdida alta o crítica
            elif risk_level in ("high", "critical"):
                # Si hay señales fuertes de giro
                if "reversal" in smart_bias or grade == "D":
                    decision = "revert"
                    allowed = True
                    decision_reasons.append(
                        "Pérdida elevada + señales fuertes de reversión → considerar revertir posición."
                    )
                else:
                    decision = "close"
                    allowed = True
                    decision_reasons.append(
                        "Pérdida elevada sin soporte técnico suficiente → cerrar posición."
                    )

        # ---------- D. REVERSIÓN (monitoreo puro) ----------
        elif context == "reversal":
            decision = "neutral"
            allowed = False

            if "reversal" in smart_bias or grade in ("D",):
                decision = "reversal-risk"
                allowed = True
                decision_reasons.append("Riesgo de reversión detectado")

        # ==========================
        # DEBUG OUTPUT (si está activo)
        # ==========================
        if DEBUG_MODE:
            try:
                entry_block = {
                    "entry_score": entry_score,
                    "entry_grade": entry_grade,
                    "entry_mode": entry_mode,
                    "entry_allowed": entry_allowed,
                    "entry_reasons": entry_reasons,
                }
                final_block = {
                    "allowed": allowed,
                    "decision": decision,
                    "decision_reasons": decision_reasons,
                    "technical_score": technical_score,
                    "match_ratio": match_ratio,
                    "grade": grade,
                    "confidence": confidence,
                    "risk_level": risk_level,
                    "roi": roi,
                    "loss_pct": loss_pct,
                }
                _debug_report(symbol, direction_hint, snapshot, entry_block, final_block)
            except Exception as e:
                logger.warning(f"⚠️ Error generando debug report: {e}")


            # PRECIO ACTUAL (último cierre)
            try:
                last_close = df_main.iloc[-1]["close"]
                result["current_price"] = float(last_close)
            except Exception:
                result["current_price"] = None


        # --------------------------------------------------------
        # 4) ESTRUCTURA FINAL
        # --------------------------------------------------------
        return {
            "symbol": symbol,
            "direction_hint": direction_hint,

            # Multi-TF
            "timeframes": timeframes,
            "major_trend": major_trend,
            "overall_trend": overall_trend,

            # Scoring base
            "match_ratio": match_ratio,
            "technical_score": technical_score,
            "grade": grade,
            "confidence": confidence,
            "confidence_label": confidence_lbl,
            "smart_bias": smart_bias,
            "divergences": divergences,

            # Decisiones globales
            "allowed": allowed,
            "decision": decision,
            "decision_reasons": decision_reasons,

            # Smart Entry integrado
            "entry_score": entry_score,
            "entry_grade": entry_grade,
            "entry_mode": entry_mode,
            "entry_allowed": entry_allowed,
            "entry_reasons": entry_reasons,

            # Datos de operación (solo si context="operation")
            "roi": roi,
            "loss_pct": loss_pct,
            "operation_risk_level": risk_level,

            # Debug
            "debug": {
                "raw_snapshot": snapshot,
                "thresholds": ctx_thr,
                "context": context,
            }
        }

    except Exception as e:
        logger.error(f"❌ Error en run_unified_analysis: {e}")
        return {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "allowed": False,
            "decision": "error",
            "decision_reasons": [str(e)],
            "roi": roi,
            "loss_pct": loss_pct,
            "debug": {"error": str(e), "context": context},
        }

