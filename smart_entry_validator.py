"""
smart_entry_validator.py — Módulo de Entrada Inteligente v1.1
-------------------------------------------------------------

Modo seleccionado: Opción 1
===========================
Filtro fuerte pero flexible:

- SOLO bloquea (entry_allowed = False) las entradas claramente peligrosas,
  clasificadas como "zona ROJA".

- Todo lo que no sea rojo se permite:
    * mode = "ok"  (verde)
    * mode = "warn" (amarillo)
  pero SIEMPRE se registran las razones en logs y en `entry_reasons`.

- La señal:
    * Se guarda en DB.
    * Puede entrar en el módulo de reactivación.
    * Podrá ser usada para entrada automática futura (si la lógica lo permite).

Entrada:
--------
evaluate_entry(symbol: str, direction: str | None, snapshot: dict)

`snapshot` viene de get_multi_tf_snapshot() y suele contener:
    - grade: "A"/"B"/"C"/"D"
    - technical_score: 0–100
    - match_ratio: 0–100
    - confidence: 0–1
    - major_trend_code: "bull"/"bear"/"sideways"
    - smart_bias_code: "continuation"/"bullish-reversal"/"bearish-reversal"/"neutral"
    - divergences: {"RSI": "...", "MACD": "..."}

Salida:
-------
{
    "symbol": str,
    "direction": str | None,
    "entry_score": float,       # 0–100
    "entry_grade": "A/B/C/D",
    "entry_mode": "ok" | "warn" | "block",
    "entry_allowed": bool,
    "entry_reasons": [str, ...]
}

NOTA:
-----
Este módulo NO envía mensajes. Solo calcula criterios de entrada.
El motor (motor_wrapper.py) ya inyecta estos campos en el resultado global
y puede usar entry_allowed para:
    - marcar allowed=False
    - ajustar la recomendación de texto
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("smart_entry_validator")


# ============================================================
# 🔍 Helper para leer campos del snapshot
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _norm_str(value: Any) -> str:
    return str(value or "").strip()


# ============================================================
# 🎯 Núcleo de evaluación de entrada
# ============================================================

def evaluate_entry(
    symbol: str,
    direction: Optional[str],
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Aplica la lógica de ENTRADA INTELIGENTE (Opción 1) sobre el snapshot técnico.

    - Identifica banderas ROJAS y AMARILLAS.
    - Calcula un `entry_score` (basado en technical_score).
    - Decide:
        * entry_mode: "ok" | "warn" | "block"
        * entry_allowed: True/False
        * entry_grade: "A/B/C/D"
        * entry_reasons: lista de textos explicativos.
    """

    direction = (direction or "").lower()
    reasons: List[str] = []

    # --- Campos básicos del snapshot ---
    grade = _norm_str(snapshot.get("grade") or snapshot.get("technical_grade") or "")
    technical_score = _safe_float(snapshot.get("technical_score"), 0.0)
    match_ratio = _safe_float(snapshot.get("match_ratio"), 50.0)
    confidence = _safe_float(snapshot.get("confidence"), 0.3)
    smart_bias = _norm_str(
        snapshot.get("smart_bias_code") or snapshot.get("smart_bias") or "neutral"
    ).lower()
    major_trend = _norm_str(
        snapshot.get("major_trend_code") or snapshot.get("major_trend") or ""
    ).lower()

    divergences = snapshot.get("divergences") or {}
    div_rsi = _norm_str(divergences.get("RSI"))
    div_macd = _norm_str(divergences.get("MACD"))

    # Contadores de banderas
    red_flags = 0
    yellow_flags = 0

    # =======================================================
    # 1) Score técnico y grade general
    # =======================================================

    # Zone D o technical_score muy bajo → bandera roja
    if grade.upper() == "D" or technical_score < 45:
        red_flags += 1
        reasons.append("📉 Score técnico muy bajo (zona D / <45).")

    # Grades intermedios (C) se consideran amarillos suaves
    elif grade.upper() == "C":
        yellow_flags += 1
        reasons.append("⚠️ Estructura técnica media (grade C).")

    # =======================================================
    # 2) Match ratio con la dirección de la señal
    # =======================================================

    if match_ratio < 40:
        red_flags += 1
        reasons.append(
            f"⚠️ Coincidencia con la tendencia muy baja (match_ratio={match_ratio:.1f}%)."
        )
    elif match_ratio < 55:
        yellow_flags += 1
        reasons.append(
            f"⚠️ Coincidencia con la tendencia solo moderada (match_ratio={match_ratio:.1f}%)."
        )

    # =======================================================
    # 3) Confianza global del motor
    # =======================================================

    if confidence < 0.28:
        red_flags += 1
        reasons.append(
            f"⚠️ Confianza global muy baja (confidence={confidence:.2f})."
        )
    elif confidence < 0.35:
        yellow_flags += 1
        reasons.append(
            f"⚠️ Confianza global media-baja (confidence={confidence:.2f})."
        )

    # =======================================================
    # 4) Smart bias y estructura vs dirección de la señal
    # =======================================================

    if direction in ("long", "short"):
        # Sesgos de reversión fuertes contra la operación
        if smart_bias == "bullish-reversal" and direction == "short":
            red_flags += 1
            reasons.append("🔄 Sesgo técnico indica reversión ALCISTA contra SHORT.")
        elif smart_bias == "bearish-reversal" and direction == "long":
            red_flags += 1
            reasons.append("🔄 Sesgo técnico indica reversión BAJISTA contra LONG.")

        # Tendencia mayor muy contraria + match bajo
        if major_trend == "bull" and direction == "short" and match_ratio < 50:
            yellow_flags += 1
            reasons.append("📈 Tendencia mayor alcista contra operación SHORT.")
        if major_trend == "bear" and direction == "long" and match_ratio < 50:
            yellow_flags += 1
            reasons.append("📉 Tendencia mayor bajista contra operación LONG.")

    # =======================================================
    # 5) Divergencias (RSI / MACD) contra la operación
    # =======================================================

    div_rsi_l = div_rsi.lower()
    div_macd_l = div_macd.lower()

    def _is_opposite_div(text: str, direction: str) -> bool:
        t = text.lower()
        if not t or not direction:
            return False

        # Alcista contra SHORT
        if "alcista" in t and direction == "short":
            return True
        # Bajista contra LONG
        if "bajista" in t and direction == "long":
            return True
        return False

    # RSI
    if _is_opposite_div(div_rsi, direction):
        # Si menciona 1h o 4h lo consideramos más serio
        if "1h" in div_rsi_l or "4h" in div_rsi_l:
            red_flags += 1
            reasons.append("⚠️ Divergencia RSI fuerte contra la operación (1h/4h).")
        else:
            yellow_flags += 1
            reasons.append("⚠️ Divergencia RSI contra la operación.")
    elif "alcista" in div_rsi_l or "bajista" in div_rsi_l:
        yellow_flags += 1
        reasons.append("ℹ️ Divergencia RSI presente (vigilar).")

    # MACD
    if _is_opposite_div(div_macd, direction):
        yellow_flags += 1
        reasons.append("⚠️ Divergencia MACD contra la operación (posible giro).")
    elif "alcista" in div_macd_l or "bajista" in div_macd_l:
        yellow_flags += 1
        reasons.append("ℹ️ Divergencia MACD presente (vigilar).")

    # =======================================================
    # 6) Cálculo de entry_score y entry_grade
    # =======================================================

    # Para v1.1 usamos technical_score como base de entry_score
    entry_score = max(0.0, min(100.0, technical_score))

    if entry_score >= 80 and red_flags == 0:
        entry_grade = "A"
    elif entry_score >= 65:
        entry_grade = "B"
    elif entry_score >= 50:
        entry_grade = "C"
    else:
        entry_grade = "D"

    # =======================================================
    # 7) Política Opción 1 — Decisión final
    # =======================================================

    """
    Opción 1:
    ---------
    - Bloquea SOLO cuando el contexto es claramente rojo:
        * red_flags >= 2, o
        * red_flags >= 1 y entry_score < 40

    - Si no bloquea:
        * mode = "warn" si hay banderas amarillas o rojas puntuales.
        * mode = "ok" si casi no hay banderas.
    """

    entry_allowed = True
    entry_mode = "ok"

    if red_flags >= 2 or (red_flags >= 1 and entry_score < 40):
        entry_allowed = False
        entry_mode = "block"
        reasons.append("⛔ Entrada bloqueada por múltiples banderas rojas.")
    elif red_flags == 1 or yellow_flags >= 2:
        entry_allowed = True
        entry_mode = "warn"
        reasons.append("🟠 Entrada permitida, pero en modo PRECAUCIÓN.")
    else:
        entry_allowed = True
        entry_mode = "ok"
        reasons.append("🟢 Condiciones de entrada aceptables.")

    # =======================================================
    # 8) Log resumido para debugging en VPS
    # =======================================================

    try:
        flags_summary = f"red={red_flags}, yellow={yellow_flags}"
        logger.info(
            f"🧠 SmartEntry[{symbol}] dir={direction or '-'} "
            f"mode={entry_mode} allowed={entry_allowed} "
            f"score={entry_score:.1f} {flags_summary} | "
            f"reasons={'; '.join(reasons)}"
        )
    except Exception:
        # No romper nunca por el log
        pass

    # =======================================================
    # 9) Respuesta normalizada
    # =======================================================

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_score": entry_score,
        "entry_grade": entry_grade,
        "entry_mode": entry_mode,
        "entry_allowed": bool(entry_allowed),
        "entry_reasons": reasons,
    }
