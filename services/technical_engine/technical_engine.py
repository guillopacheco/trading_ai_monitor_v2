# ============================================================
#  technical_engine.py — Motor técnico unificado ESTABLE
# ============================================================

import logging
from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot
from services.technical_engine.smart_entry_validator import evaluate_smart_entry
from services.technical_engine.trend_system_final import evaluate_major_trend

logger = logging.getLogger("technical_engine")


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _apply_divergence_weight(
    technical_score: float,
    confidence: float,
    divergences: dict,
    direction: str,
):
    """
    Ajusta score y confianza según divergencias.
    Retorna: (new_score, new_confidence, reasons[])
    """
    reasons = []
    score = technical_score
    conf = confidence

    rsi = (divergences or {}).get("RSI", "Ninguna")
    macd = (divergences or {}).get("MACD", "Ninguna")

    def _is_favor(div):
        return (direction == "long" and div == "alcista") or (
            direction == "short" and div == "bajista"
        )

    def _is_against(div):
        return (direction == "long" and div == "bajista") or (
            direction == "short" and div == "alcista"
        )

    favor = 0
    against = 0

    if _is_favor(rsi):
        favor += 1
    if _is_favor(macd):
        favor += 1

    if _is_against(rsi):
        against += 1
    if _is_against(macd):
        against += 1

    # Aplicar efectos
    if favor:
        delta = 5 * favor
        score += delta
        conf = min(1.0, conf + 0.05 * favor)
        reasons.append(f"Divergencia a favor (+{delta})")

    if against:
        delta = 10 * against
        score -= delta
        conf = max(0.0, conf - 0.10 * against)
        reasons.append(f"Divergencia en contra (-{delta})")

    return score, conf, reasons


# ============================================================
#   API PRINCIPAL DEL MOTOR TÉCNICO
# ============================================================
async def analyze(symbol: str, direction: str = "auto", context: str = "entry") -> dict:
    """
    Motor técnico unificado usado por:
        - SignalCoordinator
        - ReactivationEngine
        - OpenPositionEngine
        - /analizar
    """

    logger.info("\n" + "=" * 70)
    logger.info(f"🔍 Análisis técnico → {symbol} ({direction})")

    try:
        # ----------------------------------------------------
        # 1) Snapshot multi-TF (NÚCLEO)
        # ----------------------------------------------------
        snapshot = get_multi_tf_snapshot(symbol)
        if not snapshot or not isinstance(snapshot, dict):
            raise RuntimeError("Snapshot inválido o vacío")

        timeframes = snapshot.get("timeframes")
        if not timeframes or not isinstance(timeframes, list):
            raise RuntimeError("Snapshot sin timeframes válidos")

        # ----------------------------------------------------
        # 2) Dirección
        # ----------------------------------------------------
        direction = direction.lower()
        if direction == "auto":
            direction = snapshot.get("direction_hint", "long")

        # ----------------------------------------------------
        # 3) Divergencias (ya vienen normalizadas)
        # ----------------------------------------------------
        divergences = snapshot.get(
            "divergences",
            {"RSI": "Ninguna", "MACD": "Ninguna"},
        )

        # ----------------------------------------------------
        # 4) Tendencia mayor
        # ----------------------------------------------------
        major_trend = {
            "trend_label": snapshot.get("major_trend_label", "Desconocida"),
            "trend_code": snapshot.get("major_trend_code", "unknown"),
            "trend_score": _safe_float(snapshot.get("trend_score")),
        }

        # ----------------------------------------------------
        # 5) Smart Entry
        # ----------------------------------------------------
        smart_entry = evaluate_smart_entry(
            snapshot=snapshot,
            major_trend=major_trend,
            direction=direction,
        )

        # ----------------------------------------------------
        # 6) Decisión final
        # ----------------------------------------------------
        final_decision = _build_final_decision(
            snapshot=snapshot,
            smart_entry=smart_entry,
            major_trend=major_trend,
            direction=direction,
            divergences=divergences,
        )

        logger.info("📘 FINAL DECISION:\n%s", final_decision)
        logger.info("=" * 70)

        return final_decision

    except Exception as e:
        # ----------------------------------------------------
        # ❗ NUNCA devolvemos None
        # ----------------------------------------------------
        logger.exception(f"❌ Error en technical_engine.analyze({symbol}): {e}")

        return {
            "symbol": symbol,
            "context": context,
            "decision": "error",
            "allowed": False,
            "grade": None,
            "technical_score": 0.0,
            "match_ratio": 0.0,
            "confidence": 0.0,
            "divergences": {"RSI": "Ninguna", "MACD": "Ninguna"},
            "major_trend": {
                "trend_label": "Desconocida",
                "trend_code": "unknown",
                "trend_score": 0.0,
            },
            "reason": str(e),
        }


# ============================================================
#   FUSIÓN FINAL DE RESULTADOS
# ============================================================
def _build_final_decision(
    snapshot: dict,
    smart_entry: dict,
    major_trend: dict,
    direction: str,
    divergences: dict,
) -> dict:
    """
    Fusiona snapshot + smart_entry + tendencia mayor
    y genera una decisión NORMALIZADA.
    """

    match_ratio = _safe_float(snapshot.get("match_ratio"))
    base_score = _safe_float(snapshot.get("technical_score"))
    grade = snapshot.get("grade", "-")

    # Confianza base (desde smart_entry)
    base_confidence = _safe_float(smart_entry.get("entry_score")) / 100.0

    # Aplicar ponderación por divergencias
    technical_score, confidence, div_reasons = _apply_divergence_weight(
        technical_score=base_score,
        confidence=base_confidence,
        divergences=divergences,
        direction=direction,
    )

    reasons = []
    reasons.extend(div_reasons)

    # ---------------------------
    # Reglas de decisión
    # ---------------------------
    if match_ratio < 60:
        reasons.append(
            f"Coincidencia insuficiente: match={match_ratio}, score={technical_score}"
        )

    if smart_entry.get("entry_mode") == "block":
        reasons.append("Entrada bloqueada por Smart Entry")

    if major_trend.get("trend_code") in {
        "reversal",
        "bullish-reversal",
        "bearish-reversal",
    }:
        reasons.append("Contexto de reversión detectado")

    allowed = (
        match_ratio >= 60
        and smart_entry.get("entry_allowed", False)
        and smart_entry.get("entry_mode") != "block"
    )

    return {
        "symbol": snapshot.get("symbol"),
        "context": "entry",
        "decision": "enter" if allowed else "skip",
        "allowed": allowed,
        "direction": direction,
        "match_ratio": match_ratio,
        "technical_score": technical_score,
        "grade": grade,
        "confidence": confidence,
        "decision_reasons": reasons,
        "major_trend": major_trend,
        "smart_entry": smart_entry,
        "divergences": divergences,
    }


# ============================================================
#   ESTADO
# ============================================================
logger.info("✅ technical_engine.py cargado correctamente.")
