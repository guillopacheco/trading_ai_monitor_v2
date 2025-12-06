import logging
from typing import Optional, Dict, Any, List, Union

from services.technical_engine.motor_wrapper_core import get_multi_tf_snapshot

logger = logging.getLogger("trend_system_final")


# ============================================================
# THRESHOLDS Y PESOS — DEFINIDOS LOCALMENTE
# ============================================================

def get_thresholds() -> Dict[str, int]:
    return {
        "grade_A": 85,
        "grade_B": 70,
        "grade_C": 55,
    }


def get_bias_weight() -> Dict[str, float]:
    return {
        "strong": 1.0,
        "moderate": 0.7,
        "weak": 0.4,
    }


def get_score_weight() -> Dict[str, float]:
    return {
        "trend": 0.5,
        "momentum": 0.3,
        "divergence": 0.2,
    }


# ============================================================
# 🔧 Normalizadores
# ============================================================

def _normalize_direction(direction: Optional[str]) -> Optional[str]:
    if not direction:
        return None
    d = direction.lower()
    if d.startswith("long") or d.startswith("buy"):
        return "bull"
    if d.startswith("short") or d.startswith("sell"):
        return "bear"
    return None


def _normalize_trend_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    v = str(raw).lower()
    if any(k in v for k in ("bull", "alcista", "up", "alcista fuerte")):
        return "bull"
    if any(k in v for k in ("bear", "bajista", "down", "bajista fuerte")):
        return "bear"
    if any(k in v for k in ("side", "rango", "lateral")):
        return "sideways"
    return None


def _trend_label_human(code: Optional[str]) -> str:
    if code == "bull":
        return "Alcista"
    if code == "bear":
        return "Bajista"
    if code == "sideways":
        return "Lateral / Rango"
    return "Indefinida"


def _bias_label_human(code: Optional[str]) -> str:
    if code == "continuation":
        return "Continuación a favor de la señal"
    if code == "reversal":
        return "Posible reversión contra la señal"
    if code == "indecision":
        return "Indecisión / contexto mixto"
    return "Sin sesgo claro"


def _grade_from_score(score: float) -> str:
    thresholds = get_thresholds()
    if score >= thresholds["grade_A"]:
        return "A"
    if score >= thresholds["grade_B"]:
        return "B"
    if score >= thresholds["grade_C"]:
        return "C"
    return "D"


# ============================================================
# 📌 FUNCIÓN BASE
# ============================================================

def analyze_trend_core(
    symbol: Union[str, Dict[str, Any]],
    direction: Optional[str] = None,
    context: str = "entry",
    roi: Optional[float] = None,
    loss_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Motor de tendencias unificado (capa baja).

    Compatibilidad:
      - Si `symbol` es str -> se hace get_multi_tf_snapshot(symbol).
      - Si `symbol` es dict -> se interpreta como snapshot ya calculado.

    Devuelve siempre un dict con al menos:
      {
        "symbol",
        "direction",
        "context",
        "timeframes",
        "major_trend", "major_trend_label",
        "overall_trend", "overall_trend_label",
        "smart_bias", "smart_bias_code",
        "match_ratio",
        "technical_score",
        "grade",
      }
    """
    try:
        # --------------------------------------------
        # 1) Obtener snapshot
        # --------------------------------------------
        snapshot: Dict[str, Any]
        if isinstance(symbol, dict):
            snapshot = symbol
            sym = (snapshot.get("symbol") or "").upper() or "UNKNOWN"
            if direction is None:
                direction = snapshot.get("direction_hint")
        else:
            sym = (symbol or "").upper()
            snapshot = get_multi_tf_snapshot(sym)

        tf_list: List[Dict[str, Any]] = snapshot.get("timeframes") or []
        dir_code = _normalize_direction(direction)

        # --------------------------------------------
        # 2) Derivar tendencia mayor a partir de TFs
        # --------------------------------------------
        bull_weight = 0.0
        bear_weight = 0.0
        side_weight = 0.0

        for tf in tf_list:
            # Intentar distintos campos posibles
            raw_trend = (
                tf.get("trend_code")
                or tf.get("trend")
                or tf.get("trend_label")
            )
            code = _normalize_trend_label(raw_trend)
            if not code:
                continue

            # Peso simple según TF (más grande = más peso)
            tf_name = str(tf.get("tf") or tf.get("timeframe") or "")
            weight = 1.0
            try:
                if tf_name.endswith("D"):
                    weight = 3.0
                elif tf_name.endswith("H"):
                    weight = 2.0
                elif tf_name.endswith("m") or tf_name.endswith("M"):
                    weight = 1.0
            except Exception:
                weight = 1.0

            if code == "bull":
                bull_weight += weight
            elif code == "bear":
                bear_weight += weight
            elif code == "sideways":
                side_weight += weight

        if bull_weight == bear_weight == side_weight == 0:
            major_trend_code = None
        elif bull_weight >= bear_weight and bull_weight >= side_weight:
            major_trend_code = "bull"
        elif bear_weight >= bull_weight and bear_weight >= side_weight:
            major_trend_code = "bear"
        else:
            major_trend_code = "sideways"

        major_trend_label = _trend_label_human(major_trend_code)
        overall_trend_code = major_trend_code
        overall_trend_label = major_trend_label

        # --------------------------------------------
        # 3) Smart bias respecto a la señal
        # --------------------------------------------
        smart_bias_code: Optional[str] = None
        if dir_code and major_trend_code:
            if dir_code == major_trend_code:
                smart_bias_code = "continuation"
            elif dir_code != major_trend_code:
                smart_bias_code = "reversal"
        else:
            smart_bias_code = "indecision"

        smart_bias_label = _bias_label_human(smart_bias_code)

        # --------------------------------------------
        # 4) match_ratio y technical_score básicos
        # --------------------------------------------
        # Base neutra
        match_ratio = 50.0

        # Ajuste por alineación de tendencia/bias
        if smart_bias_code == "continuation":
            match_ratio += 20.0
        elif smart_bias_code == "reversal":
            match_ratio -= 20.0
        elif smart_bias_code == "indecision":
            match_ratio += 0.0

        # Refuerzo según número de TF disponibles
        n_tfs = len(tf_list)
        if n_tfs >= 3:
            match_ratio += 10.0
        elif n_tfs == 2:
            match_ratio += 5.0
        elif n_tfs == 1:
            match_ratio += 2.0

        # Límite 0–100
        match_ratio = max(0.0, min(match_ratio, 100.0))

        # Technical score por ahora similar al match_ratio
        technical_score = float(match_ratio)
        grade = _grade_from_score(technical_score)

        return {
            "symbol": sym,
            "direction": dir_code,
            "context": context,
            "timeframes": tf_list,
            "major_trend": major_trend_code,
            "major_trend_label": major_trend_label,
            "overall_trend": overall_trend_code,
            "overall_trend_label": overall_trend_label,
            "smart_bias": smart_bias_label,
            "smart_bias_code": smart_bias_code,
            "match_ratio": match_ratio,
            "technical_score": technical_score,
            "grade": grade,
            "n_timeframes": n_tfs,
            "raw_snapshot_status": snapshot.get("status"),
        }

    except Exception as e:
        logger.error(f"❌ Error en analyze_trend_core: {e}")
        # Fallback muy defensivo
        return {
            "symbol": str(symbol),
            "direction": _normalize_direction(direction),
            "context": context,
            "timeframes": [],
            "major_trend": None,
            "major_trend_label": _trend_label_human(None),
            "overall_trend": None,
            "overall_trend_label": _trend_label_human(None),
            "smart_bias": _bias_label_human(None),
            "smart_bias_code": None,
            "match_ratio": 0.0,
            "technical_score": 0.0,
            "grade": "D",
            "n_timeframes": 0,
            "raw_snapshot_status": "error",
            "error": str(e),
        }


# ============================================================
# ⚙️ API PÚBLICA (para reactivadores, reversals, telegram, etc.)
# ============================================================

def _get_thresholds() -> Dict[str, int]:
    return get_thresholds()


# Alias por compatibilidad hacia atrás
get_thresholds_public = _get_thresholds
