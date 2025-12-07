"""application_layer.py — Capa de aplicación del Trading AI Monitor

Esta capa es el **punto de entrada único** hacia el motor técnico.
Desde aquí se exponen funciones de alto nivel que pueden usar:

- command_bot.py  → para /analizar MANUAL
- futuros servicios (reversiones, operaciones abiertas, etc.)

La idea es que **ningún módulo de interfaz** (Telegram, cron jobs, etc.)
llame directamente a trend_system_final / technical_engine,
sino que lo haga a través de este archivo.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import logging

# Motor técnico unificado (opción C validada)
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("application_layer")


# ================================================================
# 🔧 Normalizadores básicos (símbolo y dirección)
# ================================================================
def _normalize_symbol(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip().upper()
    # Quitar separadores típicos: BTC/USDT → BTCUSDT
    s = s.replace("/", "").replace(" ", "")
    return s


def _normalize_direction(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None

    d = raw.strip().lower()
    # Mapear equivalentes comunes
    if d in {"long", "buy", "compra", "comprar", "up", "📈"}:
        return "long"
    if d in {"short", "sell", "venta", "vender", "down", "📉"}:
        return "short"

    # Si no se reconoce, devolvemos None y dejamos que el motor infiera
    return None


# ================================================================
# 🧠 API PRINCIPAL — ANÁLISIS MANUAL
# ================================================================
def manual_analysis(
    symbol_raw: str,
    direction_raw: Optional[str] = None,
    context: str = "entry",
) -> Dict[str, Any]:
    """Realiza un análisis técnico manual usando el motor unificado.

    Esta función será el **único punto** que deberían usar:
    - /analizar en command_bot.py
    - pruebas manuales desde otros módulos

    Devuelve:
        {
            "symbol": str,
            "direction": Optional[str],
            "context": str,
            "engine_result": dict,   # resultado crudo del motor
            "summary": str           # mensaje listo para Telegram
        }
    """
    symbol = _normalize_symbol(symbol_raw)
    direction = _normalize_direction(direction_raw)

    if not symbol:
        raise ValueError("Símbolo vacío o inválido para análisis manual")

    # Normalizar context "manual" → "entry" (misma lógica técnica)
    if context == "manual":
        context = "entry"

    logger.info(
        "📨 [AppLayer] Análisis manual solicitado: %s (%s, ctx=%s)",
        symbol,
        direction or "auto",
        context,
    )

    # ------------------------------------------------------------
    # 1) Llamar al motor técnico unificado
    # ------------------------------------------------------------
    engine_result = engine_analyze(
        symbol=symbol,
        direction_hint=direction,
        context=context,
        roi=None,
        loss_pct=None,
    )

    # ------------------------------------------------------------
    # 2) Construir resumen amigable tipo Telegram
    # ------------------------------------------------------------
    major_trend = engine_result.get("major_trend_label", "Desconocida")
    bias_code = engine_result.get("smart_bias_code") or engine_result.get(
        "smart_bias", "neutral"
    )
    grade = engine_result.get("grade", "?")
    confidence = engine_result.get("confidence", 0.0)
    decision = engine_result.get("decision", "wait")
    ctx_used = engine_result.get("context", context or "entry")
    match_ratio = float(engine_result.get("match_ratio", 0.0))
    tech_score = float(engine_result.get("technical_score", 0.0))

    # Confianza en %, admitiendo que a veces ya viene en 0–1 y otras en 0–100
    if confidence <= 1.0:
        conf_pct = round(confidence * 100.0, 1)
    else:
        conf_pct = round(confidence, 1)

    reasons = engine_result.get("decision_reasons") or []
    main_reason = reasons[0] if reasons else "Sin motivo detallado."

    header_side = direction or "auto"

    lines: list[str] = [
        f"📊 Análisis de {symbol} ({header_side})",
        f"• Tendencia mayor: {major_trend}",
        f"• Smart Bias: {bias_code}",
        f"• Confianza: {conf_pct:.1f}% (Grado {grade})",
        "",
        f"📌 Recomendación: {decision} ({conf_pct:.1f}% confianza)",
        f"➡️ Acción sugerida: {decision}",
        f"📝 Motivo principal: {main_reason}",
        "",
        f"ℹ️ Contexto analizado: {ctx_used}",
        f"ℹ️ match_ratio={match_ratio:.1f} | score={tech_score:.1f}",
    ]

    summary = "\n".join(lines)

    logger.info(
        "✅ [AppLayer] Análisis manual completado: %s (%s) → decision=%s, grade=%s, conf=%.1f%%",
        symbol,
        direction or "auto",
        decision,
        grade,
        conf_pct,
    )

    return {
        "symbol": symbol,
        "direction": direction,
        "context": ctx_used,
        "engine_result": engine_result,
        "summary": summary,
    }
