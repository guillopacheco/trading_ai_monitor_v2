"""
technical_engine.py — Motor Único de Análisis Técnico (2025)

Unifica en un solo punto:

    ✔ multi-TF snapshot  (motor_wrapper_core.get_multi_tf_snapshot)
    ✔ match_ratio + technical_score + grade + smart_bias + divergencias
    ✔ Smart Entry (A–D + ok/warn/block)
    ✔ Lógica por contexto:
        - entry         → señal nueva
        - reactivation  → reactivación de señal pendiente
        - reversal      → riesgo de reversión
        - operation     → seguimiento de operación abierta
        - manual        → análisis /analizar

Toda la app debe usar SIEMPRE este motor para conseguir coherencia
entre análisis de señales, reactivaciones, seguimiento y /analizar.
"""

import logging
import pprint

from config import DEBUG_MODE              # ya existe en tu proyecto :contentReference[oaicite:3]{index=3}
from motor_wrapper_core import get_multi_tf_snapshot  # snapshot multi-TF :contentReference[oaicite:4]{index=4}
from smart_entry_validator import evaluate_entry      # Smart Entry integrado :contentReference[oaicite:5]{index=5}

logger = logging.getLogger("technical_engine")


# ============================================================
# 🔢 Thresholds unificados por contexto
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
    "internal": {
        "min_match": 45,
        "min_score": 40,
    },
    # Para seguimiento de operaciones abiertas
    "operation": {
        "min_match": 45,
        "min_score": 40,
    },
    # Para reversión profunda / peligro
    "reversal": {
        "min_match": 40,
        "min_score": 35,
    },
}

def get_thresholds():
    """
    Exporta thresholds en formato simple para otros módulos
    (compatibilidad con motor_wrapper / monitores).
    """
    return {
        "entry": THRESHOLDS["entry"]["min_match"],
        "reactivation": THRESHOLDS["reactivation"]["min_match"],
        "internal": THRESHOLDS["internal"]["min_match"],
        "operation": THRESHOLDS["operation"]["min_match"],
        "reversal": THRESHOLDS["reversal"]["min_match"],
    }


# ============================================================
# 🎛️ Normalizadores
# ============================================================

def _trend_label(code: int | None) -> str:
    return {
        2: "bullish",
        1: "slightly-bullish",
        0: "neutral",
        -1: "slightly-bearish",
        -2: "bearish",
    }.get(code, "neutral")


def _confidence_label(c: float) -> str:
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

    logger.info("\n📌 SNAPSHOT MULTI-TF (raw):")
    try:
        logger.info(pprint.pformat(snapshot, indent=4, compact=False))
    except Exception:
        logger.info(str(snapshot))

    logger.info("\n🎯 SMART ENTRY:")
    try:
        logger.info(pprint.pformat(entry, indent=4))
    except Exception:
        logger.info(str(entry))

    logger.info("\n📘 FINAL DECISION:")
    try:
        logger.info(pprint.pformat(final, indent=4))
    except Exception:
        logger.info(str(final))

    logger.info("=" * 70 + "\n")


# ============================================================
# 🧠 Motor ÚNICO de análisis
# ============================================================

def analyze(
    symbol: str,
    direction_hint: str | None = None,
    context: str = "entry",
    *,
    roi: float | None = None,
    loss_pct: float | None = None,
):
    """
    Motor técnico principal.

    Parámetros:
        symbol         → par, ej. 'BTCUSDT'
        direction_hint → 'long'/'short' o None
        context        → 'entry' | 'reactivation' | 'reversal' | 'operation' | 'manual'
        roi            → ROI actual de la operación (si aplica, en % incluyendo apalancamiento)
        loss_pct       → pérdida sin apalancamiento (si aplica, en %)

    Devuelve SIEMPRE un diccionario estándar:
        {
          symbol, direction_hint,
          timeframes, major_trend, overall_trend,
          match_ratio, technical_score, grade,
          confidence, confidence_label, smart_bias, divergences,
          allowed, decision, decision_reasons,
          entry_score, entry_grade, entry_mode,
          entry_allowed, entry_reasons,
          debug: {...}
        }
    """

    # Normalizar context manual → entry (misma lógica técnica)
    if context == "manual":
        context = "entry"

    try:
        # --------------------------------------------------------
        # 1) MULTI-TF SNAPSHOT (core principal)
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
        entry_info = evaluate_entry(symbol, direction_hint, snapshot)

        entry_score = entry_info.get("entry_score", 0)
        entry_grade = entry_info.get("entry_grade", "D")
        entry_mode = entry_info.get("entry_mode", "block")
        entry_allowed = entry_info.get("entry_allowed", False)
        entry_reasons = entry_info.get("entry_reasons", [])

        # --------------------------------------------------------
        # 3) DECISIÓN PRINCIPAL (por contexto)
        # --------------------------------------------------------
        decision = "wait"
        decision_reasons: list[str] = []
        allowed = False

        # Thresholds por contexto
        ctx_thr = THRESHOLDS.get(context, THRESHOLDS["entry"])
        min_match = ctx_thr["min_match"]
        min_score = ctx_thr["min_score"]

        # ---------- A. ENTRADA (señal nueva / manual) ----------
        if context == "entry":
            if match_ratio >= min_match and technical_score >= min_score:
                allowed = True
                decision = "enter"
                decision_reasons.append(
                    f"Alineación suficiente: match={match_ratio:.1f}, score={technical_score:.1f}"
                )
            else:
                allowed = False
                decision = "skip"
                decision_reasons.append(
                    f"Coincidencia insuficiente: match={match_ratio:.1f}, score={technical_score:.1f}"
                )

            # Ajustes por divergencias / smart_bias de reversión
            if "reversal" in str(smart_bias) or (
                "bearish" in str(divergences).lower()
                or "bullish" in str(divergences).lower()
            ):
                if allowed and entry_grade in ("A", "B"):
                    # Se permite, pero con advertencia
                    decision = "enter"
                    allowed = True
                    if entry_mode != "ok":
                        entry_mode = "warn"
                    decision_reasons.append("Divergencias / smart_bias de reversión detectadas.")
                else:
                    # Estructura débil → mejor evitar
                    allowed = False
                    decision = "skip"
                    decision_reasons.append("Reversión fuerte detectada → evitar entrada.")

            # Bloqueo final si Smart Entry dice bloqueado
            if entry_mode == "block":
                allowed = False
                decision = "skip"
                decision_reasons.append("Entrada bloqueada por Smart Entry.")

        # ---------- B. REACTIVACIÓN ----------
        elif context == "reactivation":
            if match_ratio >= min_match and technical_score >= min_score:
                allowed = True
                decision = "reactivate"
                decision_reasons.append(
                    f"Condiciones favorables: match={match_ratio:.1f}, score={technical_score:.1f}"
                )
            else:
                decision = "wait"
                allowed = False
                decision_reasons.append(
                    f"Condiciones insuficientes para reactivar (match={match_ratio:.1f}, score={technical_score:.1f})."
                )

            # Penalización por reversión fuerte
            if "reversal" in str(smart_bias) and (grade == "D" or entry_grade == "D"):
                allowed = False
                decision = "wait"
                decision_reasons.append("Reversión fuerte detectada → esperar para reactivar.")

        # ---------- C. REVERSIÓN (riesgo severo) ----------
        elif context == "reversal":
            decision = "neutral"
            allowed = False

            # Dispara riesgo si la estructura técnica es mala
            if "reversal" in str(smart_bias) or grade == "D":
                decision = "reversal-risk"
                allowed = True
                decision_reasons.append("Riesgo de reversión detectado por estructura técnica.")

            # Si además hay pérdida fuerte (sin apalancamiento) refuerza señal
            if loss_pct is not None and loss_pct <= -3.0:
                if decision != "reversal-risk":
                    decision = "reversal-risk"
                    allowed = True
                decision_reasons.append(f"Pérdida sin apalancamiento {loss_pct:.2f}% < -3.0%.")

        # ---------- D. OPERACIÓN ABIERTA (seguimiento general) ----------
        elif context == "operation":
            # Aquí no decidimos solo con técnico; también se usa ROI/loss_pct
            # para abrir espacio a lógicas como las de operation_tracker.py :contentReference[oaicite:6]{index=6}
            decision = "hold"
            allowed = True

            # Base: si la estructura es mala → al menos "watch"
            if grade in ("D",) or match_ratio < min_match:
                decision = "watch"
                decision_reasons.append(
                    f"Estructura débil: grade={grade}, match={match_ratio:.1f}."
                )

            # Pérdida técnica + pérdida real → sugerir cierre o reversión
            if loss_pct is not None:
                if loss_pct <= -3.0:
                    decision_reasons.append(
                        f"Pérdida sin apalancamiento relevante: {loss_pct:.2f}%."
                    )
                if loss_pct <= -5.0 and ("reversal" in str(smart_bias) or grade == "D"):
                    decision = "close"
                    decision_reasons.append(
                        "Tendencia mayor en contra + pérdida fuerte → sugerencia de cierre."
                    )

            # ROI (incluyendo apalancamiento): si muy negativo con estructura mala → revertir
            if roi is not None and roi <= -50.0:
                if "reversal" in str(smart_bias) or grade in ("D",):
                    decision = "revert"
                    decision_reasons.append(
                        f"ROI crítico ({roi:.1f}%) + smart_bias de reversión → sugerencia de revertir."
                    )

        # ---------- E. CONTEXTO DESCONOCIDO ----------
        else:
            decision = "unknown"
            allowed = False
            decision_reasons.append(f"Contexto desconocido: {context}")

        # --------------------------------------------------------
        # 4) DEBUG (si está activado)
        # --------------------------------------------------------
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
                    "context": context,
                    "roi": roi,
                    "loss_pct": loss_pct,
                }
                _debug_report(symbol, direction_hint, snapshot, entry_block, final_block)
            except Exception as e:
                logger.warning(f"⚠️ Error generando debug report: {e}")

        # --------------------------------------------------------
        # 5) RESPUESTA FINAL ESTÁNDAR
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

            # Debug
            "debug": {
                "raw_snapshot": snapshot,
                "thresholds": ctx_thr,
                "context": context,
                "roi": roi,
                "loss_pct": loss_pct,
            },
        }

    except Exception as e:
        logger.error(f"❌ Error en technical_engine.analyze({symbol}): {e}")
        return {
            "symbol": symbol,
            "direction_hint": direction_hint,
            "allowed": False,
            "decision": "error",
            "decision_reasons": [str(e)],
            "debug": {"error": str(e), "context": context},
        }
