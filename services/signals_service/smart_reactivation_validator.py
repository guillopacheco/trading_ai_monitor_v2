"""
smart_reactivation_validator.py
--------------------------------
Módulo de VALIDACIÓN DE REACTIVACIÓN INTELIGENTE (v2 unificado).

Objetivo:
- Usar el MISMO motor técnico unificado que el resto de la app.
- Dejar de hacer consultas OHLCV independientes.
- Relajar la exigencia de tener siempre 15m + 1h:
    * Si faltan 15m o 1h, se usan los timeframes disponibles.
    * Solo se bloquea si REALMENTE no hay datos.

Flujo:
1) Llama a motor_wrapper.analyze_for_reactivation(symbol, side) (o fallback a analyze()).
2) Usa el snapshot multi–TF (ya con fallback desde motor_wrapper_core).
3) Evalúa:
    - Alineación de tendencia mayor vs lado de la señal.
    - Sesgo inteligente (smart_bias).
    - Puntuación técnica global.
    - Decisión base del motor (allowed/decision).
4) Devuelve:
    - decision: "reactivate" | "wait" | "cancel"
    - score: 0–100
    - reasons: lista de explicaciones.
    - scores/metrics: detalle para logs y depuración.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from services.technical_engine import motor_wrapper

logger = logging.getLogger("smart_reactivation")


# ============================================================
# 📦 Dataclass de salida
# ============================================================

@dataclass
class ReactivationDecision:
    symbol: str
    side: str
    decision: str
    score: float
    reasons: List[str]
    scores: Dict[str, float]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 🧮 Utilidades internas
# ============================================================

def _side_to_trend_code(side: str) -> Optional[str]:
    """
    Convierte el lado de la señal a código de tendencia del motor.
    long  -> "bull"
    short -> "bear"
    """
    if not side:
        return None
    s = side.lower()
    if s.startswith("long") or s.startswith("buy"):
        return "bull"
    if s.startswith("short") or s.startswith("sell"):
        return "bear"
    return None


def _classify_grade(score: float) -> str:
    """Convierte puntaje global 0–100 a etiqueta simple."""
    if score >= 75:
        return "strong"
    if score >= 55:
        return "medium"
    return "weak"


def _eval_reactivation_from_snapshot(
    symbol: str,
    side: str,
    motor_result: Dict[str, Any],
    divergences_hint: Optional[Dict[str, str]] = None,
) -> ReactivationDecision:
    """
    Núcleo de la lógica de reactivación, usando solo el resultado del motor unificado.
    NO hace consultas a Bybit; solo interpreta snapshot + decisión base.
    """

    snapshot = motor_result.get("snapshot") or {}
    tf_list: List[Dict[str, Any]] = snapshot.get("timeframes") or []
    engine_decision = motor_result.get("decision") or {}
    engine_allowed = bool(engine_decision.get("allowed", False))
    engine_decision_code = engine_decision.get("decision", "wait")

    major_trend_code = snapshot.get("major_trend_code")
    major_trend_label = snapshot.get("major_trend_label") or major_trend_code
    smart_bias = snapshot.get("smart_bias_code") or snapshot.get("smart_bias")
    technical_score = snapshot.get("technical_score")
    snapshot_grade = snapshot.get("grade")
    match_ratio = snapshot.get("match_ratio")

    side_code = _side_to_trend_code(side)

    reasons: List[str] = []
    scores: Dict[str, float] = {}

    # --------------------------------------------------------
    # 1) Validación mínima de datos
    # --------------------------------------------------------
    if not tf_list:
        reasons.append("Sin datos suficientes en los timeframes analizados.")
        decision = "wait"
        total_score = 0.0
        scores = {"trend_score": 0.0, "bias_score": 0.0, "tech_component": 0.0}
        metrics = {
            "major_trend": major_trend_label,
            "smart_bias": smart_bias,
            "technical_score": technical_score,
            "snapshot_grade": snapshot_grade,
            "match_ratio": match_ratio,
            "n_timeframes": 0,
            "engine_decision": engine_decision,
        }
        return ReactivationDecision(
            symbol=symbol,
            side=side,
            decision=decision,
            score=total_score,
            reasons=reasons,
            scores=scores,
            metrics=metrics,
        )

    # Número de TFs disponibles (ya con fallback manejado por motor_wrapper_core)
    n_tfs = len(tf_list)

    # --------------------------------------------------------
    # 2) Puntaje por alineación de tendencia
    # --------------------------------------------------------
    trend_score = 0.0
    if side_code and major_trend_code:
        if side_code == major_trend_code:
            trend_score = 40.0
            reasons.append("Tendencia mayor alineada con el lado de la señal.")
        else:
            trend_score = 10.0
            reasons.append("Tendencia mayor en posible conflicto con el lado de la señal.")
    else:
        trend_score = 20.0
        reasons.append("Tendencia mayor poco definida; se evalúan más factores.")

    # --------------------------------------------------------
    # 3) Puntaje por smart_bias
    # --------------------------------------------------------
    bias_score = 0.0
    if smart_bias:
        sb = str(smart_bias).lower()
        is_bull = "bull" in sb or "alcista" in sb
        is_bear = "bear" in sb or "bajista" in sb
        is_reversal = "reversal" in sb or "revers" in sb

        if side_code == "bull" and is_bull and not is_reversal:
            bias_score = 40.0
            reasons.append("Sesgo inteligente claramente alcista, a favor de un LONG.")
        elif side_code == "bear" and is_bear and not is_reversal:
            bias_score = 40.0
            reasons.append("Sesgo inteligente claramente bajista, a favor de un SHORT.")
        elif is_reversal:
            bias_score = 10.0
            reasons.append("El motor detecta contexto de posible reversión.")
        else:
            bias_score = 20.0
            reasons.append("Sesgo inteligente mixto o neutro.")
    else:
        bias_score = 20.0
        reasons.append("Sin sesgo inteligente claro; se ponderan más factores.")

    # --------------------------------------------------------
    # 4) Puntaje por technical_score global
    # --------------------------------------------------------
    if isinstance(technical_score, (int, float)):
        tech_raw = max(0.0, min(float(technical_score), 100.0))
        tech_component = tech_raw * 0.3  # máximo aporte 30 pts
    else:
        tech_component = 20.0
        reasons.append("Puntuación técnica no disponible; se asume contexto medio.")

    # Refuerzo leve por cantidad de TFs disponibles
    if n_tfs >= 3:
        tech_component += 5.0
    elif n_tfs == 2:
        tech_component += 2.0

    # --------------------------------------------------------
    # 5) Ajuste por divergencias (hint externo)
    # --------------------------------------------------------
    if divergences_hint:
        # Ejemplo de estructura esperada:
        # {"RSI": "bajista (1h)", "MACD": "ninguna"}
        for k, v in divergences_hint.items():
            if not v:
                continue
            v_low = v.lower()
            if side_code == "bull" and "bajista" in v_low:
                tech_component -= 10.0
                reasons.append(f"Divergencia {k} bajista en contra de un LONG.")
            if side_code == "bear" and "alcista" in v_low:
                tech_component -= 10.0
                reasons.append(f"Divergencia {k} alcista en contra de un SHORT.")

    # --------------------------------------------------------
    # 6) Puntaje total y clasificación
    # --------------------------------------------------------
    total_score = max(0.0, min(trend_score + bias_score + tech_component, 100.0))
    global_grade = _classify_grade(total_score)

    scores = {
        "trend_score": round(trend_score, 2),
        "bias_score": round(bias_score, 2),
        "tech_component": round(tech_component, 2),
    }

    # --------------------------------------------------------
    # 7) Decisión final basada en score + motor
    # --------------------------------------------------------
    decision = "wait"

    # Caso 1: contexto fuerte + motor lo permite -> reactivar
    if (
        global_grade == "strong"
        and engine_allowed
        and engine_decision_code in ("enter", "reactivate", "continue", "open")
    ):
        decision = "reactivate"
        reasons.append("Contexto fuerte y motor técnico permite reactivar/entrar.")

    # Caso 2: contexto muy débil o reversión fuerte en contra -> cancelar
    elif global_grade == "weak":
        decision = "cancel"
        reasons.append("Contexto técnico débil o contradictorio; alta probabilidad de fallo.")

    # Caso 3: contexto medio o motor indeciso -> esperar
    else:
        decision = "wait"
        reasons.append("Contexto mixto; mejor esperar nueva revisión antes de reactivar.")

    metrics = {
        "major_trend": major_trend_label,
        "major_trend_code": major_trend_code,
        "smart_bias": smart_bias,
        "technical_score": technical_score,
        "snapshot_grade": snapshot_grade,
        "global_grade": global_grade,
        "match_ratio": match_ratio,
        "n_timeframes": n_tfs,
        "engine_decision": engine_decision,
    }

    return ReactivationDecision(
        symbol=symbol,
        side=side,
        decision=decision,
        score=round(total_score, 2),
        reasons=reasons,
        scores=scores,
        metrics=metrics,
    )


# ============================================================
# 🌟 API PÚBLICA
# ============================================================

def evaluate_reactivation(
    symbol: str,
    side: str,
    entry_price: Optional[float] = None,
    divergences_hint: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Punto único de entrada para validar reactivación.

    Compatibilidad hacia atrás:
    - Mantiene la misma firma básica (symbol, side, entry_price, divergences_hint, **kwargs).
    - Devuelve un dict con:
        {
            "symbol": ...,
            "side": ...,
            "decision": "reactivate" | "wait" | "cancel",
            "score": float,
            "reasons": [...],
            "scores": {...},
            "metrics": {...}
        }
    """

    logger.info(f"♻️ Evaluando reactivación inteligente para {symbol} ({side})…")

    # 1) Intentar usar API dedicada de reactivación
    try:
        analyze_fn = getattr(motor_wrapper, "analyze_for_reactivation", None)
        if callable(analyze_fn):
            motor_result = analyze_fn(symbol, side)
        else:
            # Fallback: usar analyze() genérico
            logger.warning(
                "⚠️ motor_wrapper.analyze_for_reactivation no existe; usando analyze() genérico."
            )
            analyze_generic = getattr(motor_wrapper, "analyze", None)
            if callable(analyze_generic):
                motor_result = analyze_generic(symbol, side)
            else:
                raise RuntimeError(
                    "motor_wrapper no expone analyze_for_reactivation ni analyze()."
                )
    except Exception as e:
        logger.error(f"❌ Error llamando al motor unificado para reactivación: {e}")
        # Fallback ultra conservador
        fallback_decision = ReactivationDecision(
            symbol=symbol,
            side=side,
            decision="wait",
            score=0.0,
            reasons=[f"Error interno del motor de reactivación: {e}"],
            scores={"trend_score": 0.0, "bias_score": 0.0, "tech_component": 0.0},
            metrics={},
        )
        return fallback_decision.to_dict()

    # 2) Interpretar snapshot + decisión base del motor
    try:
        decision_obj = _eval_reactivation_from_snapshot(
            symbol=symbol,
            side=side,
            motor_result=motor_result,
            divergences_hint=divergences_hint,
        )
        return decision_obj.to_dict()
    except Exception as e:
        logger.error(f"❌ Error interpretando resultado del motor unificado: {e}")
        fallback_decision = ReactivationDecision(
            symbol=symbol,
            side=side,
            decision="wait",
            score=0.0,
            reasons=[f"Error interpretando análisis técnico: {e}"],
            scores={"trend_score": 0.0, "bias_score": 0.0, "tech_component": 0.0},
            metrics={"raw_motor_result_type": str(type(motor_result))},
        )
        return fallback_decision.to_dict()
