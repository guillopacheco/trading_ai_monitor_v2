"""
trend_system_final.py — Motor técnico de alto nivel (versión wrapper 2025-11)
-----------------------------------------------------------------------------

Este módulo:

- Usa motor_wrapper_core.get_multi_tf_snapshot() para obtener el análisis
  multi-temporalidad del símbolo.
- Aplica reglas de decisión:
  * allowed / no allowed
  * match_ratio y umbrales por ANALYSIS_MODE
  * interpretación de divergencias y smart_bias
- Expone dos funciones PÚBLICAS (API estable):

  ✔ analyze_trend_core(symbol, direction_hint=None) -> dict
  ✔ analyze_and_format(symbol, direction_hint=None) -> (dict, markdown_str)

Otros módulos que lo usan:
- telegram_reader (señales nuevas)
- command_bot (/analizar)
- signal_reactivation_sync (reactivación automática)
- position_reversal_monitor (reversiones peligrosas)

⚠️ IMPORTANTE:
Mantener esta API estable evita romper el resto de la app.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Tuple, Optional

from config import ANALYSIS_MODE
from motor_wrapper_core import get_multi_tf_snapshot

logger = logging.getLogger("trend_system_final")


# ============================================================
# 🎚 Umbrales según modo de análisis
# ============================================================
def _get_thresholds() -> Dict[str, float]:
    """
    Devuelve los umbrales usados por el resto del sistema:

    - internal:      mínimo de match_ratio para considerar técnicamente aceptable.
    - reactivation:  mínimo de match_ratio para reactivar una señal.
    - strong:        match_ratio considerado muy fuerte.
    """
    mode = (ANALYSIS_MODE or "balanced").lower()

    if mode == "aggressive":
        return {
            "internal": 55.0,
            "reactivation": 65.0,
            "strong": 80.0,
        }
    elif mode == "conservative":
        return {
            "internal": 65.0,
            "reactivation": 75.0,
            "strong": 85.0,
        }
    else:  # balanced (valor por defecto)
        return {
            "internal": 60.0,
            "reactivation": 70.0,
            "strong": 82.0,
        }


# ============================================================
# 🧠 Motor de decisión de alto nivel
# ============================================================
def analyze_trend_core(
    symbol: str,
    direction_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analiza la estructura de mercado y devuelve un dict con la
    información suficiente para que otros módulos tomen decisiones.

    Retorno típico:
    {
      "symbol": "EPICUSDT",
      "direction": "long" / "short" / None,
      "major_trend": "Alcista",
      "overall_trend": "Alcista fuerte",
      "match_ratio": 87.5,
      "allowed": True / False,
      "confidence": 0.63,
      "confidence_label": "🟢 Alta" / "🟡 Media" / "🔴 Baja",
      "smart_bias": "Reversión alcista",
      "divergences": { "RSI": "...", "MACD": "..." },
      "timeframes": {
          "15m": "Alcista",
          "30m": "Bajista",
          "1h": "Alcista",
          "4h": "Sin datos" / ...
      },
      "debug": {...}  # datos adicionales si se quieren loguear.
    }
    """
    direction_hint = (direction_hint or "").lower()
    if direction_hint not in ("long", "short"):
        direction_hint = None

    # 1) Obtener snapshot multi-TF
    snapshot = get_multi_tf_snapshot(symbol, direction_hint=direction_hint)

    tf_map = {}
    for tf_res in snapshot["timeframes"]:
        tf_map[tf_res["tf_label"]] = tf_res["trend_label"]

    major_trend_label = snapshot["major_trend_label"]
    major_trend_code = snapshot["major_trend_code"]
    match_ratio = snapshot["match_ratio"]
    divergences = snapshot["divergences"]
    smart_bias_code = snapshot["smart_bias_code"]
    confidence = snapshot["confidence"]

    thresholds = _get_thresholds()
    internal_thr = thresholds["internal"]
    strong_thr = thresholds["strong"]

    # 2) Overall trend (texto más humano)
    aligned_tfs = list(tf_map.values()).count(major_trend_label)
    total_tfs = len(tf_map) if tf_map else 1
    align_ratio = aligned_tfs / total_tfs

    if align_ratio >= 0.75:
        overall_trend = f"{major_trend_label} fuerte"
    elif align_ratio <= 0.4:
        overall_trend = f"{major_trend_label} débil / mercado mixto"
    else:
        overall_trend = f"{major_trend_label} moderada"

    # 3) Smart bias en texto
    smart_bias_human = {
        "bullish-reversal": "Reversión alcista",
        "bearish-reversal": "Reversión bajista",
        "continuation": "Continuación de tendencia",
        "neutral": "Neutral / sin sesgo claro",
    }.get(smart_bias_code, "Neutral / sin sesgo claro")

    # 4) Confianza → etiqueta
    if confidence >= 0.65:
        conf_label = "🟢 Alta"
    elif confidence >= 0.4:
        conf_label = "🟡 Media"
    else:
        conf_label = "🔴 Baja"

    # 5) allowed / no allowed (según divergencias y match_ratio)
    allowed = True
    reasons: list[str] = []

    if direction_hint:
        dir_txt = "LONG" if direction_hint == "long" else "SHORT"
        reasons.append(f"Dirección sugerida: {dir_txt}.")

    # Penalizar si match_ratio bajo
    if match_ratio < internal_thr:
        allowed = False
        reasons.append(
            f"Match_ratio bajo ({match_ratio:.1f}% < {internal_thr:.1f}%)."
        )

    # Divergencias en contra de la dirección
    div_text = f"{divergences.get('RSI','')} {divergences.get('MACD','')}"
    if direction_hint == "long" and ("Bajista" in div_text):
        reasons.append("Divergencias bajistas contra LONG.")
        # si además la confianza es baja, anulamos
        if confidence < 0.55:
            allowed = False

    if direction_hint == "short" and ("Alcista" in div_text):
        reasons.append("Divergencias alcistas contra SHORT.")
        if confidence < 0.55:
            allowed = False

    # Smart bias contrario
    if direction_hint == "long" and smart_bias_code == "bearish-reversal":
        reasons.append("Smart bias indica posible giro bajista.")
        if confidence < 0.7:
            allowed = False

    if direction_hint == "short" and smart_bias_code == "bullish-reversal":
        reasons.append("Smart bias indica posible giro alcista.")
        if confidence < 0.7:
            allowed = False

    # Si no hay dirección_hint, nunca bloqueamos totalmente, solo avisamos
    if direction_hint is None:
        allowed = True

    result: Dict[str, Any] = {
        "symbol": symbol,
        "direction": direction_hint,
        "major_trend": major_trend_label,
        "overall_trend": overall_trend,
        "match_ratio": float(match_ratio),
        "allowed": bool(allowed),
        "confidence": float(confidence),
        "confidence_label": conf_label,
        "smart_bias": smart_bias_human,
        "divergences": divergences,
        "timeframes": tf_map,
        "reasons": reasons,
        "debug": {
            "major_trend_code": major_trend_code,
            "raw_snapshot": snapshot,
            "thresholds": thresholds,
        },
    }

    return result


# ============================================================
# 📝 Formateo para Telegram
# ============================================================
def analyze_and_format(
    symbol: str,
    direction_hint: Optional[str] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Función que usan:

    - /analizar (command_bot)
    - telegram_reader (señales nuevas)
    - signal_reactivation_sync (reactivación)
    - position_reversal_monitor (reversiones)

    Devuelve:
      result_dict, mensaje_markdown
    """
    result = analyze_trend_core(symbol, direction_hint=direction_hint)

    tf_lines = []
    # Queremos un orden coherente: 15m, 30m, 1h, 4h (si existen)
    order = ["15m", "30m", "1h", "4h", "5m", "1m"]
    tfs = result.get("timeframes", {})

    for label in order:
        if label in tfs:
            tf_lines.append(f"🔹 {label}: {tfs[label]}")
    # Añadir cualquier TF extra
    for label, trend in tfs.items():
        if label not in order:
            tf_lines.append(f"🔹 {label}: {trend}")

    major_trend = result["major_trend"]
    overall_trend = result["overall_trend"]
    match_ratio = result["match_ratio"]
    divergences = result["divergences"]
    smart_bias = result["smart_bias"]
    conf_label = result["confidence_label"]
    confidence = result["confidence"]
    allowed = result["allowed"]
    direction = result["direction"]

    # Texto de divergencias
    div_parts = []
    if divergences.get("RSI") and divergences["RSI"] != "Ninguna":
        div_parts.append(f"RSI: {divergences['RSI']}")
    if divergences.get("MACD") and divergences["MACD"] != "Ninguna":
        div_parts.append(f"MACD: {divergences['MACD']}")
    div_text = ", ".join(div_parts) if div_parts else "Ninguna"

    # Dirección en texto
    dir_line = ""
    match_line = ""
    if direction:
        dir_text = direction.upper()
        dir_line = f"🎯 Dirección sugerida: {dir_text}\n"
        match_line = f"📊 Coincidencia con la tendencia: {match_ratio:.1f}%\n"

    # Confianza texto simple (además del emoji)
    if confidence >= 0.65:
        conf_text = "Alta"
    elif confidence >= 0.4:
        conf_text = "Media"
    else:
        conf_text = "Baja"

    # Recomendación final
    rec = ""

    thresholds = _get_thresholds()
    internal_thr = thresholds["internal"]
    strong_thr = thresholds["strong"]

    warning_suffix = ""
    if "Bajista" in div_text or "Alcista" in div_text:
        warning_suffix = " (⚠️ Divergencia técnica detectada.)"

    if not direction:
        # Modo exploratorio (/analizar sin dirección)
        rec = (
            f"📌 Escenario actual: {overall_trend}. "
            f"Smart bias: {smart_bias}. "
            f"Confianza: {conf_text}."
        )
    else:
        if allowed:
            if match_ratio >= strong_thr and confidence >= 0.6:
                rec = (
                    "✅ Señal confirmada (alta coincidencia con la tendencia)."
                )
            elif match_ratio >= internal_thr:
                rec = (
                    "✅ Señal aceptable, pero con algunas condiciones a vigilar."
                )
            else:
                rec = (
                    "⚠️ Señal marginal: la coincidencia con la tendencia es limitada."
                )
        else:
            rec = (
                "❌ Condiciones técnicas poco favorables para la dirección indicada."
            )

        if warning_suffix:
            rec = f"{rec}{warning_suffix}"

    lines = [
        f"📊 Análisis de {symbol}",
        *tf_lines,
        "",
        f"🧭 Tendencia mayor: {major_trend}",
        f"📈 Estructura global: {overall_trend}",
    ]

    if direction:
        lines.append(dir_line.rstrip())
        lines.append(match_line.rstrip())

    lines.extend(
        [
            f"🧪 Divergencias: {div_text}",
            f"🧬 Sesgo técnico (smart): {smart_bias}",
            f"🧮 Confianza global: {conf_label} ({conf_text})",
            "",
            f"📌 Recomendación: {rec}",
        ]
    )

    message = "\n".join(lines)

    return result, message
