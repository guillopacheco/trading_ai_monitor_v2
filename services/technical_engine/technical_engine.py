# ============================================================
#  technical_engine.py — Motor técnico unificado REAL
# ============================================================

import logging
from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot
from services.technical_engine.smart_entry_validator import evaluate_smart_entry
from services.technical_engine.trend_system_final import evaluate_major_trend
from services.technical_engine.smart_divergences import detect_divergences
from services.helpers import safe_float

logger = logging.getLogger("technical_engine")


# ============================================================
#   API PRINCIPAL DEL MOTOR TÉCNICO
# ============================================================
async def analyze(symbol: str, direction: str = "auto", context: str = "entry") -> dict:
    """
    Motor técnico unificado usado por:
        - /analizar
        - ReactivationEngine
        - OpenPositionEngine
        - SignalCoordinator
    """
    logger.info("\n" + "=" * 70)

    try:
        # 1) Snapshot multi-temporalidad desde el wrapper
        snapshot = await get_multi_tf_snapshot(symbol)
        if not snapshot or "timeframes" not in snapshot:
            raise RuntimeError("Snapshot inválido o incompleto.")

        # 2) Dirección inferida si es "auto"
        direction = direction.lower()
        if direction == "auto":
            direction = snapshot.get("direction_hint", "long")

        # 3) Divergencias RSI/MACD
        divs = detect_divergences(snapshot)

        # 4) Tendencia mayor
        major_trend = evaluate_major_trend(snapshot)

        # 5) Evaluación Smart Entry
        smart_entry = evaluate_smart_entry(snapshot, major_trend, direction)

        # 6) Fusión final de decisión
        final_decision = _build_final_decision(
            snapshot, smart_entry, major_trend, direction
        )

        # 7) Unificación del debug log
        logger.info("📘 FINAL DECISION:\n%s", final_decision)
        logger.info("=" * 70)

        return final_decision

    except Exception as e:
        logger.exception(f"❌ Error en technical_engine.analyze({symbol}): {e}")
        return {
            "allowed": False,
            "decision": "error",
            "reason": str(e),
            "symbol": symbol,
        }


# ============================================================
#   FUSIÓN DE RESULTADOS
# ============================================================
def _build_final_decision(
    snapshot: dict, smart_entry: dict, major_trend: dict, direction: str
) -> dict:
    """
    Fusiona los datos técnicos para crear la decisión final normalizada.
    """
    match_ratio = safe_float(snapshot.get("match_ratio"))
    technical_score = safe_float(snapshot.get("technical_score"))
    grade = snapshot.get("grade", "-")

    reasons = []

    # Reglas de decisión
    if match_ratio < 60:
        reasons.append(
            f"Coincidencia insuficiente: match={match_ratio}, score={technical_score}"
        )

    if smart_entry.get("entry_mode") == "block":
        reasons.append("Entrada bloqueada por Smart Entry.")

    if major_trend.get("trend_code") in [
        "reversal",
        "bullish-reversal",
        "bearish-reversal",
    ]:
        reasons.append("Señal de reversión detectada.")

    allowed = (
        match_ratio >= 60
        and smart_entry.get("entry_allowed", False)
        and smart_entry.get("entry_mode") != "block"
    )

    return {
        "symbol": snapshot["symbol"],
        "context": "entry",
        "decision": "enter" if allowed else "skip",
        "allowed": allowed,
        "direction": direction,
        "match_ratio": match_ratio,
        "technical_score": technical_score,
        "grade": grade,
        "confidence": smart_entry.get("entry_score", 0) / 100,
        "decision_reasons": reasons,
        "major_trend": major_trend,
        "smart_entry": smart_entry,
        "divergences": snapshot.get("divergences", {}),
    }


# ============================================================
#   IMPORTANTE: ELIMINAMOS analyze_market
# ============================================================

# ❌ ESTA FUNCIÓN NO DEBE EXISTIR:
# - Llamaba a funciones inexistentes
# - Rompía la arquitectura
# - Generaba errores silenciosos
#
# async def analyze_market(...):
#     ...
#
# 🔥 Eliminada permanentemente.


# ============================================================
#   MOTOR COMPLETO Y ESTABLE
# ============================================================
logger.info("technical_engine.py cargado exitosamente.")
