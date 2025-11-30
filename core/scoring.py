"""
core/scoring.py
--------------------
Cálculo de puntuaciones (scores) y match_ratio para el Motor Técnico A+.

Este módulo:
- Recibe señales crudas o semi-normalizadas
- Usa core.normalizer para homogenizar en escala 0–100
- Devuelve un bundle listo para usar en technical_brain_unified
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any

from core import normalizer as nz


@dataclass
class ScoreBundle:
    trend: float
    momentum: float
    volatility: float
    divergence: float
    structure: float
    micro: float
    smart_entry: float
    technical_score: float
    match_ratio: float
    grade: str
    confidence: float
    risk_class: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Alias útil
        d["score"] = d["technical_score"]
        return d


# ================================================================
# 🎓 Helpers
# ================================================================

def _grade_from_score(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _confidence_from_score(score: float, risk_score: float) -> float:
    """
    Devuelve 0–100, donde >70 es confianza alta.
    Penaliza si el riesgo es alto (risk_score bajo).
    """
    base = score
    adj = (risk_score - 50) * 0.4
    val = base + adj
    return max(0.0, min(100.0, val))


def _risk_class_from_scores(volatility_score: float, divergence_score: float) -> str:
    """
    Clasificación textual de riesgo: low / medium / high
    usando volatilidad + divergencias.
    """
    # baja vol + pocas divergencias → bajo riesgo
    if volatility_score >= 65 and divergence_score >= 50:
        return "low"
    # zona media → riesgo medio
    if 40 <= volatility_score < 65:
        return "medium"
    # volatilidad muy baja pero divergencias fuertes, o vol alta → riesgo alto
    return "high"


# ================================================================
# 🧮 Cálculo de bundle de scores
# ================================================================

def build_score_bundle(
    *,
    trend_raw: float | None,
    momentum_raw: float | None,
    volatility_raw: float | None,
    divergence_raw: Any,
    structure_raw: str | None,
    micro_raw: float | None,
    smart_entry_raw: float | None,
) -> ScoreBundle:
    """
    Construye un ScoreBundle a partir de insumos crudos.

    Todos los parámetros pueden ser None; se reemplazan por 50 (neutral).
    """

    # 1) Normalización a escala 0–100
    trend = nz.normalize_trend(trend_raw)
    momentum = nz.normalize_momentum(momentum_raw)
    volatility = nz.normalize_volatility(volatility_raw)
    divergence = nz.normalize_divergence(divergence_raw)
    structure = nz.normalize_structure(structure_raw or "unknown")
    micro = nz.normalize_micro(micro_raw)
    smart_entry = smart_entry_raw if smart_entry_raw is not None else 50.0

    # 2) Score técnico con pesos base (luego podemos hacerlos dinámicos)
    w_trend = 0.30
    w_momentum = 0.20
    w_volatility = 0.10
    w_divergence = 0.15
    w_structure = 0.10
    w_micro = 0.10
    w_smart = 0.05

    technical_score = (
        trend * w_trend
        + momentum * w_momentum
        + volatility * w_volatility
        + divergence * w_divergence
        + structure * w_structure
        + micro * w_micro
        + smart_entry * w_smart
    )

    # 3) match_ratio (más conservador, menos peso al smart_entry)
    w_trend_m = 0.35
    w_momentum_m = 0.20
    w_volatility_m = 0.10
    w_divergence_m = 0.20
    w_structure_m = 0.10
    w_micro_m = 0.05

    match_ratio = (
        trend * w_trend_m
        + momentum * w_momentum_m
        + volatility * w_volatility_m
        + divergence * w_divergence_m
        + structure * w_structure_m
        + micro * w_micro_m
    )

    # 4) Riesgo & confianza
    # Por ahora riesgo "neutral" (1). Podremos tunearlo según contexto.
    risk_score = nz.normalize_risk(1)
    risk_class = _risk_class_from_scores(volatility, divergence)
    confidence = _confidence_from_score(technical_score, risk_score)

    # 5) Calificación cualitativa
    grade = _grade_from_score(technical_score)

    return ScoreBundle(
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        divergence=divergence,
        structure=structure,
        micro=micro,
        smart_entry=smart_entry,
        technical_score=technical_score,
        match_ratio=match_ratio,
        grade=grade,
        confidence=confidence,
        risk_class=risk_class,
    )
