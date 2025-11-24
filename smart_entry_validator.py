"""
smart_entry_validator.py — Motor profesional de decisión de entrada
-------------------------------------------------------------------

Este módulo NO descarga datos ni calcula indicadores.
Trabaja ÚNICAMENTE con el snapshot multi-TF generado por:

    motor_wrapper_core.get_multi_tf_snapshot()

Y decide:

- Si tiene sentido entrar en la operación (entry_allowed)
- Qué tan buena es la entrada (entry_score y entry_grade A–D)
- Si la lógica sugiere un escenario más tipo swing o tipo scalp (entry_mode)
- Explica por qué (entry_reasons)

Se centra en:

- Tendencia mayor vs dirección de la señal
- Coherencia multi-TF (4h, 1h, 30m, 15m, 5m)
- Momentum (RSI)
- Relación EMA corta / EMA larga en TF bajos (timing de entrada)
- Divergencias RSI / MACD contra la señal
- Smart bias y confianza global del motor
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("smart_entry_validator")


# ============================================================
# Utilidades internas
# ============================================================
def _normalize_direction(direction_hint: Optional[str]) -> Optional[str]:
    """
    Normaliza la dirección a 'long' / 'short' / None.
    """
    if not direction_hint:
        return None
    d = direction_hint.lower()
    if d.startswith("long") or d == "buy":
        return "long"
    if d.startswith("short") or d == "sell":
        return "short"
    return None


def _build_tf_index(snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Crea un índice por tf_label (ej: '4h', '1h', '30m', '15m', '5m')
    para acceder rápidamente a la info de cada timeframe.
    """
    idx: Dict[str, Dict[str, Any]] = {}
    for tf_res in snapshot.get("timeframes", []) or []:
        label = tf_res.get("tf_label") or tf_res.get("tf") or ""
        if label:
            idx[str(label)] = tf_res
    return idx


def _grade_from_score(score: float) -> str:
    """
    Convierte un score 0–100 a una letra A–D.
    """
    if score >= 80.0:
        return "A"
    if score >= 65.0:
        return "B"
    if score >= 50.0:
        return "C"
    return "D"


# ============================================================
# Núcleo: evaluación de entrada
# ============================================================
def evaluate_entry(
    symbol: str,
    direction_hint: Optional[str],
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluador profesional de ENTRADA.

    Params:
      symbol:
        Par analizado, ej: 'PIPPINUSDT'.
      direction_hint:
        'long' / 'short' / None. Si es None, se asume modo exploratorio.
      snapshot:
        Dict devuelto por get_multi_tf_snapshot(), típicamente:

        {
          "symbol": "...",
          "direction_hint": "long/short/None",
          "timeframes": [
             {
               "tf": "60",
               "tf_label": "1h",
               "trend_label": "Alcista",
               "trend_code": "bull/bear/sideways",
               "votes_bull": int,
               "votes_bear": int,
               "rsi": float,
               "macd_hist": float,
               "ema_short": float,
               "ema_long": float,
               "close": float,
               "atr": float,
               "div_rsi": "alcista/bajista/ninguna",
               "div_macd": "alcista/bajista/ninguna",
             },
             ...
          ],
          "major_trend_label": "...",
          "major_trend_code": "bull/bear/sideways",
          "trend_score": float 0–1,
          "match_ratio": float 0–100,
          "divergences": { "RSI": "...", "MACD": "..." },
          "smart_bias_code": "...",
          "confidence": float 0–1,
          ...
        }

    Return:
      Un dict con:

      {
        "entry_allowed": bool,          # ¿Tiene sentido entrar?
        "entry_score": float,           # 0–100
        "entry_grade": "A"|"B"|"C"|"D", # más alto = mejor
        "entry_mode": "swing"|"scalp"|"neutral",
        "entry_reasons": [str, ...],    # explicación legible
      }
    """
    direction = _normalize_direction(direction_hint)
    reasons: List[str] = []

    # Si no hay dirección (modo exploratorio), damos score neutro y no bloqueamos.
    match_ratio = float(snapshot.get("match_ratio", 50.0) or 50.0)
    confidence = float(snapshot.get("confidence", 0.0) or 0.0)
    divergences = snapshot.get("divergences") or {}
    smart_bias_code = snapshot.get("smart_bias_code")
    major_trend_code = snapshot.get("major_trend_code")

    if direction is None:
        base_score = match_ratio
        # Ajuste ligero por confianza
        if confidence >= 0.7:
            base_score += 5.0
        elif confidence < 0.4:
            base_score -= 5.0

        score = max(0.0, min(base_score, 100.0))
        grade = _grade_from_score(score)
        reasons.append("Modo exploratorio: sin filtro estricto de entrada.")
        return {
            "entry_allowed": True,
            "entry_score": score,
            "entry_grade": grade,
            "entry_mode": "neutral",
            "entry_reasons": reasons,
        }

    # A partir de aquí: hay una dirección concreta (LONG / SHORT)
    tf_index = _build_tf_index(snapshot)
    score = match_ratio  # punto de partida
    reasons.append(f"Match ratio base del motor: {match_ratio:.1f}%.")

    # ------------------------------------------------------------
    # 1) Tendencia mayor vs dirección
    # ------------------------------------------------------------
    want_code = "bull" if direction == "long" else "bear"
    if major_trend_code == want_code:
        score += 8.0
        reasons.append("Dirección alineada con la tendencia mayor.")
    elif major_trend_code in ("bull", "bear"):
        score -= 12.0
        reasons.append("Dirección va contra la tendencia mayor.")
    else:
        reasons.append("Tendencia mayor lateral / mixta.")

    # ------------------------------------------------------------
    # 2) Coherencia multi-TF (4h, 1h, 30m, 15m, 5m)
    # ------------------------------------------------------------
    weights = {
        "4h": 2.0,
        "1h": 1.6,
        "30m": 1.3,
        "15m": 1.0,
        "5m": 0.8,
    }

    def _dir_code_ok(code: str) -> bool:
        if direction == "long":
            return code == "bull"
        return code == "bear"

    for label, w in weights.items():
        tf = tf_index.get(label)
        if not tf:
            continue

        code = tf.get("trend_code")
        if not code:
            continue

        # Tendencia TF vs dirección
        if _dir_code_ok(code):
            score += 2.5 * w
        elif code in ("bull", "bear"):
            score -= 3.0 * w

        # Momentum RSI dentro de cada TF
        rsi_val = tf.get("rsi")
        rsi = float(rsi_val) if rsi_val is not None else None
        if rsi is not None:
            if direction == "long":
                if rsi >= 55:
                    score += 1.5 * w
                elif rsi <= 45:
                    score -= 1.5 * w
            else:
                if rsi <= 45:
                    score += 1.5 * w
                elif rsi >= 55:
                    score -= 1.5 * w

    # ------------------------------------------------------------
    # 3) EMA en marcos bajos (timing de entrada)
    # ------------------------------------------------------------
    low_tf = tf_index.get("15m") or tf_index.get("30m") or tf_index.get("5m")
    if low_tf:
        ema_s = low_tf.get("ema_short")
        ema_l = low_tf.get("ema_long")
        if ema_s is not None and ema_l is not None:
            if direction == "long":
                if ema_s > ema_l:
                    score += 6.0
                    reasons.append(
                        "EMA rápida por encima de lenta en marco bajo (impulso alcista activo)."
                    )
                else:
                    score -= 8.0
                    reasons.append(
                        "EMA rápida por debajo de lenta en marco bajo (entrada contra el impulso)."
                    )
            else:  # short
                if ema_s < ema_l:
                    score += 6.0
                    reasons.append(
                        "EMA rápida por debajo de lenta en marco bajo (impulso bajista activo)."
                    )
                else:
                    score -= 8.0
                    reasons.append(
                        "EMA rápida por encima de lenta en marco bajo (entrada contra el impulso)."
                    )

    # ------------------------------------------------------------
    # 4) Divergencias (RSI / MACD)
    # ------------------------------------------------------------
    div_rsi_text = str(divergences.get("RSI") or divergences.get("rsi") or "").lower()
    div_macd_text = str(divergences.get("MACD") or divergences.get("macd") or "").lower()

    if direction == "long":
        if "bajista" in div_rsi_text or "bajista" in div_macd_text:
            score -= 15.0
            reasons.append("Divergencias bajistas contra un LONG (posible rebote/corrección).")
    else:  # short
        if "alcista" in div_rsi_text or "alcista" in div_macd_text:
            score -= 15.0
            reasons.append("Divergencias alcistas contra un SHORT (posible rebote fuerte).")

    # ------------------------------------------------------------
    # 5) Smart bias + confianza global
    # ------------------------------------------------------------
    if smart_bias_code == "continuation":
        score += 4.0
        reasons.append("Smart bias indica continuación de tendencia.")
    elif smart_bias_code in ("bullish-reversal", "bearish-reversal"):
        # Si la reversión va en contra de la operación, penalizamos más
        if (direction == "long" and smart_bias_code == "bearish-reversal") or (
            direction == "short" and smart_bias_code == "bullish-reversal"
        ):
            score -= 10.0
            reasons.append("Smart bias advierte posible giro en contra de la operación.")
        else:
            score -= 4.0
            reasons.append("Contexto de giro general, se reduce la agresividad.")

    if confidence >= 0.7:
        score += 4.0
        reasons.append("Confianza global del motor alta.")
    elif confidence < 0.4:
        score -= 6.0
        reasons.append("Confianza global del motor baja.")

    # Clamp del score
    score = max(0.0, min(score, 100.0))
    grade = _grade_from_score(score)

    # ------------------------------------------------------------
    # 6) Clasificar modo: swing vs scalp
    # ------------------------------------------------------------
    swing_like = False
    scalp_like = False

    high_tf = tf_index.get("4h") or tf_index.get("1h")
    if high_tf and _dir_code_ok(high_tf.get("trend_code", "")):
        swing_like = True

    if low_tf and _dir_code_ok(low_tf.get("trend_code", "")):
        scalp_like = True

    if swing_like and not scalp_like:
        entry_mode = "swing"
    elif scalp_like and not swing_like:
        entry_mode = "scalp"
    elif swing_like and scalp_like:
        # Cuando coinciden ambas, lo consideramos swing
        entry_mode = "swing"
    else:
        entry_mode = "neutral"

    # ------------------------------------------------------------
    # 7) Decisión final: ¿permitir la entrada o no?
    # ------------------------------------------------------------
    entry_allowed = True

    # Regla principal: por debajo de 50 → no entra
    if score < 50.0:
        entry_allowed = False
        reasons.append(f"Score de entrada bajo ({score:.1f} < 50).")

    # Regla extra: score MUY bajo + divergencias fuertes en contra
    if score < 45.0:
        if (
            direction == "long"
            and ("bajista" in div_rsi_text or "bajista" in div_macd_text)
        ) or (
            direction == "short"
            and ("alcista" in div_rsi_text or "alcista" in div_macd_text)
        ):
            entry_allowed = False
            reasons.append(
                "Divergencias fuertes contra la señal con score muy bajo: entrada descartada."
            )

    return {
        "entry_allowed": entry_allowed,
        "entry_score": float(score),
        "entry_grade": grade,
        "entry_mode": entry_mode,
        "entry_reasons": reasons,
    }
