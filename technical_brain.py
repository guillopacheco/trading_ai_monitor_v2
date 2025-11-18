"""
technical_brain.py
------------------------------------------------------------
UNIFICADOR CENTRAL DE ANÁLISIS TÉCNICO

Este módulo reúne TODA la lógica técnica en un solo lugar:

✓ Tendencias multi-TF (1m–3m–5m–15m–30m–1h–4h)
✓ Divergencias (RSI / MACD + Smart Divergence)
✓ ATR y volatilidad relativa
✓ Match técnico (% de coincidencia con la señal)
✓ Lógica de entrada, reversión y reactivación
✓ Reportes listos para enviar por Telegram

EL RESTO DEL SISTEMA SOLO LLAMA:
- analyze_for_entry()
- analyze_for_reactivation()
- analyze_for_reversal()
- quick_tf_scan()

------------------------------------------------------------
"""

import logging
import math
from typing import Dict, Any, List, Tuple

from indicators import get_technical_data
from smart_divergences import detect_smart_divergence
from divergence_detector import detect_divergences

logger = logging.getLogger("technical_brain")


# ============================================================
# 🔧 CONFIGURACIÓN GLOBAL DEL MOTOR
# ============================================================

TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h"]

MAJOR_TF = ["1h", "4h"]
MID_TF = ["15m", "30m"]
LOW_TF = ["1m", "3m", "5m"]

THRESHOLDS = {
    "entry_min_match": 70,
    "reactivation_min_match": 80,
    "reversal_loss_trigger": -3,
}


# ============================================================
# 🔍 DETECCIÓN DE TENDENCIA GLOBAL
# ============================================================

def _extract_trend(tech: Dict[str, Any]) -> str:
    """
    Produce un veredicto de tendencia global usando 1h+4h.
    """
    votes = []

    for tf in MAJOR_TF:
        trend = tech.get(tf, {}).get("trend", "").lower()

        if "bull" in trend or "alcista" in trend:
            votes.append("bull")
        elif "bear" in trend or "bajista" in trend:
            votes.append("bear")

    if votes.count("bull") > votes.count("bear"):
        return "alcista"
    if votes.count("bear") > votes.count("bull"):
        return "bajista"
    return "neutral"


# ============================================================
# 📊 ATR & VOLATILIDAD
# ============================================================

def _atr_volatility(tech: Dict[str, Any], symbol: str) -> Tuple[float, float, str]:
    """
    ATR relativo = ATR / precio.
    Devuelve:
    - atr
    - atr_relativo
    - etiqueta de volatilidad
    """
    try:
        base = tech["1m"]
        atr = base.get("atr", 0)
        price = base.get("close", 0)
        if not atr or not price:
            return 0, 0, "DESCONOCIDA"

        relative = atr / price

        if relative > 0.015:
            label = "MUY ALTA"
        elif relative > 0.01:
            label = "ALTA"
        elif relative > 0.005:
            label = "MEDIA"
        else:
            label = "BAJA"

        return atr, relative, label

    except Exception:
        return 0, 0, "DESCONOCIDA"


# ============================================================
# 🎯 MATCH TÉCNICO
# ============================================================

def _calc_match_ratio(direction: str, tech: Dict[str, Any]) -> float:
    """
    Calcula coincidencia técnica en porcentaje.
    """
    score = 0
    total = 6  # 1m–3m–5m–15m–30m–1h consideran

    for tf in ["1m", "3m", "5m", "15m", "30m", "1h"]:
        trend = tech.get(tf, {}).get("trend", "").lower()
        if direction == "long" and ("bull" in trend or "alcista" in trend):
            score += 1
        if direction == "short" and ("bear" in trend or "bajista" in trend):
            score += 1

    return (score / total) * 100


# ============================================================
# 🧠 ANALIZADOR CENTRAL
# ============================================================

def analyze_market(symbol: str, direction_hint: str | None = None) -> Dict[str, Any]:
    """
    Obtiene:
    ✓ tech multi-TF
    ✓ divergencias
    ✓ ATR & volatilidad
    ✓ tendencia global
    ✓ match técnico
    ✓ reporte formateado
    """
    tech = get_technical_data(symbol, intervals=TIMEFRAMES)
    if not tech:
        raise ValueError(f"Sin datos técnicos para {symbol}")

    # Divergencias
    raw_divs = detect_divergences(symbol, tech)
    smart = detect_smart_divergence(symbol, tech)

    # ATR / volatilidad
    atr, atr_rel, vol_label = _atr_volatility(tech, symbol)

    # Tendencia global
    global_trend = _extract_trend(tech)

    # Match técnico
    if direction_hint:
        match = _calc_match_ratio(direction_hint.lower(), tech)
    else:
        match = 0

    formatted = _format_report(symbol, tech, raw_divs, smart, global_trend, atr, atr_rel, vol_label, match)

    return {
        "symbol": symbol,
        "tech": tech,
        "direction_hint": direction_hint,
        "divergences": raw_divs,
        "smart_divergence": smart,
        "atr": atr,
        "atr_relative": atr_rel,
        "volatility": vol_label,
        "major_trend": global_trend,
        "match_ratio": match,
        "report": formatted,
    }


# ============================================================
# 📄 GENERADOR DE REPORTE
# ============================================================

def _format_report(symbol, tech, raw_divs, smart, major, atr, atr_rel, vol, match):
    lines = [
        f"📊 *Análisis técnico de {symbol}*",
        "",
        f"🌐 Tendencia Global (1h–4h): *{major.upper()}*",
        f"⚡ Volatilidad: *{vol}* (ATR={atr:.6f} | rel={atr_rel:.4f})",
        "",
        "📈 *Tendencias:*",
    ]

    for tf in ["1m", "3m", "5m", "15m", "30m", "1h", "4h"]:
        trend = tech.get(tf, {}).get("trend", "N/A")
        lines.append(f"• {tf}: {trend}")

    lines.append("")
    lines.append("🔍 *Divergencias:*")
    lines.append(f"• RSI: {raw_divs.get('RSI', 'N/A')}")
    lines.append(f"• MACD: {raw_divs.get('MACD', 'N/A')}")
    lines.append(f"• Smart: {smart}")

    if match:
        lines.append("")
        lines.append(f"🎯 *Match técnico:* {match:.1f}%")

    return "\n".join(lines)


# ============================================================
# 🎯 MODO DE ENTRADA
# ============================================================

def analyze_for_entry(symbol: str, direction: str) -> Dict[str, Any]:
    r = analyze_market(symbol, direction_hint=direction)

    allowed = r["match_ratio"] >= THRESHOLDS["entry_min_match"] and r["major_trend"] != "neutral"

    r["allowed"] = allowed
    return r


# ============================================================
# ♻️ MODO DE REACTIVACIÓN
# ============================================================

def analyze_for_reactivation(symbol: str, direction: str, entry_price: float) -> Dict[str, Any]:
    r = analyze_market(symbol, direction_hint=direction)

    if r["match_ratio"] < THRESHOLDS["reactivation_min_match"]:
        r["allowed"] = False
        r["reason"] = "Match técnico insuficiente"
        return r

    if direction == "long" and r["major_trend"] == "bajista":
        r["allowed"] = False
        r["reason"] = "Tendencia mayor en contra"
        return r

    if direction == "short" and r["major_trend"] == "alcista":
        r["allowed"] = False
        r["reason"] = "Tendencia mayor en contra"
        return r

    r["allowed"] = True
    r["reason"] = "Condiciones óptimas"
    return r


# ============================================================
# 🚨 MODO REVERSIÓN
# ============================================================

def analyze_for_reversal(symbol: str, direction: str, price_change_pct: float) -> Dict[str, Any]:
    """
    price_change_pct = cambio SIN apalancamiento
    """
    r = analyze_market(symbol, direction_hint=direction)

    if price_change_pct > THRESHOLDS["reversal_loss_trigger"]:
        r["alert"] = False
        r["reason"] = "Pérdida insuficiente"
        return r

    # Divergencias fuertes siempre alertan
    divs = r["divergences"]
    smart = r["smart_divergence"]

    div_block = (
        ("bear" in smart.lower() and direction == "long") or
        ("bull" in smart.lower() and direction == "short")
    )

    trend_flip = (
        direction == "long" and r["major_trend"] == "bajista"
    ) or (
        direction == "short" and r["major_trend"] == "alcista"
    )

    if div_block or trend_flip:
        r["alert"] = True
        r["reason"] = "Divergencias o tendencia mayor en contra"
    else:
        r["alert"] = False
        r["reason"] = "Condiciones sin riesgo extremo"

    return r


# ============================================================
# 🚀 ESCANEO RÁPIDO
# ============================================================

def quick_tf_scan(symbol: str) -> Dict[str, Any]:
    tech = get_technical_data(symbol, intervals=["5m", "15m", "1h"])
    if not tech:
        raise ValueError("Sin datos técnicos")

    return {
        "symbol": symbol,
        "trend_5m": tech["5m"]["trend"],
        "trend_15m": tech["15m"]["trend"],
        "trend_1h": tech["1h"]["trend"],
    }
