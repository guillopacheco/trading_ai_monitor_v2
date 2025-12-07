"""
application_layer.py
====================

Capa intermedia entre Telegram/Bybit y el motor técnico unificado.

OBJETIVOS:
- Normalizar datos de entrada (señales, comandos, posiciones).
- Llamar SIEMPRE al motor técnico a través de un único punto:
    👉 technical_brain_unified.run_unified_analysis(...)
- Traducir decisiones técnicas a acciones de alto nivel:
    - REACTIVATE / IGNORE para señales
    - hold / exit / reverse para operaciones
    - mensajes amigables para Telegram (/analizar)
- Evitar que Telegram/Bybit conozcan detalles internos del motor.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.technical_engine.technical_brain_unified import run_unified_analysis

logger = logging.getLogger("application")


# ============================================================================
# 🔧 Helpers internos
# ============================================================================

def _norm_direction(direction: Optional[str]) -> Optional[str]:
    """Normaliza un string a 'long' / 'short' / None."""
    if not direction:
        return None
    d = direction.strip().lower()
    if d.startswith("long") or d.startswith("buy"):
        return "long"
    if d.startswith("short") or d.startswith("sell"):
        return "short"
    return None


def _first_reason(reasons: Any, default: str = "Sin motivo detallado.") -> str:
    """Devuelve el primer motivo legible desde una lista o string."""
    if isinstance(reasons, list) and reasons:
        return str(reasons[0])
    if isinstance(reasons, str) and reasons:
        return reasons
    return default


# ============================================================================
# 🟦 1) Análisis manual (usado por /analizar)
# ============================================================================

async def manual_analysis(symbol: str, direction: str = "auto") -> str:
    """
    Envuelve el motor técnico unificado y devuelve un mensaje amigable
    para Telegram (/analizar).

    - symbol: par en Bybit, ej. BTCUSDT
    - direction: "long", "short" o "auto" (auto = sin sesgo de lado)
    """
    try:
        dir_hint = None if direction == "auto" else _norm_direction(direction)

        # Usamos el contexto "entry" para análisis manual de nuevas entradas.
        engine_result: Dict[str, Any] = run_unified_analysis(
            symbol=symbol,
            direction_hint=dir_hint,
            context="entry",
            roi=None,
            loss_pct=None,
        )

        snapshot: Dict[str, Any] = engine_result.get("snapshot", {}) or {}
        decision: Dict[str, Any] = engine_result.get("decision", {}) or {}
        smart_entry: Dict[str, Any] = engine_result.get("smart_entry", {}) or {}

        major_trend = snapshot.get("major_trend_label", "") or "N/A"
        smart_bias = snapshot.get("smart_bias", "") or "N/A"
        grade = snapshot.get("grade", decision.get("grade", "D"))
        match_ratio = float(snapshot.get("match_ratio", decision.get("match_ratio", 0.0)))
        tech_score = float(snapshot.get("technical_score", decision.get("technical_score", 0.0)))
        confidence = float(decision.get("confidence", snapshot.get("confidence", 0.0)))

        final_decision = str(decision.get("decision", "wait"))
        main_reason = _first_reason(decision.get("decision_reasons"))

        entry_allowed = bool(smart_entry.get("entry_allowed", False))
        entry_grade = smart_entry.get("entry_grade", grade)
        entry_mode = smart_entry.get("entry_mode", "ok")
        entry_score = float(smart_entry.get("entry_score", tech_score))
        entry_reason = _first_reason(smart_entry.get("entry_reasons"))

        direction_label = direction if direction != "auto" else (dir_hint or "auto")

        msg = (
            f"📊 *Análisis de {symbol} ({direction_label})*\n"
            f"• Tendencia mayor: *{major_trend}*\n"
            f"• Smart Bias: *{smart_bias}*\n"
            f"• Confianza global: *{confidence*100:.1f}%* (Grado {grade})\n"
            f"• Match técnico: *{match_ratio:.1f}%* | Score: *{tech_score:.1f}*\n\n"
            f"🎯 *Smart Entry*\n"
            f"• Permitido: *{'Sí' if entry_allowed else 'No'}* (modo: {entry_mode}, grado {entry_grade})\n"
            f"• Score entrada: *{entry_score:.1f}*\n"
            f"• Motivo principal: {entry_reason}\n\n"
            f"📌 *Decisión final del motor*\n"
            f"• Decisión: *{final_decision}* ({confidence*100:.1f}% confianza)\n"
            f"• Motivo principal: {main_reason}\n\n"
            f"ℹ️ Contexto analizado: *entry*\n"
        )
        return msg

    except Exception as e:
        logger.exception("❌ Error en manual_analysis(%s)", symbol)
        return f"❌ Error analizando {symbol}: {e}"


# ============================================================================
# 🟦 2) Evaluación para “reactivación de señales”
# ============================================================================

async def evaluate_signal_reactivation(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa si una señal pendiente debería reactivarse usando el motor unificado.

    Espera un dict con al menos:
        {
            "symbol": "BTCUSDT",
            "direction": "long"/"short"/"buy"/"sell"/etc.
            ... (otros campos pueden existir, pero no son obligatorios aquí)
        }

    Devuelve:
        {
            "symbol": str,
            "direction": str,
            "decision": str,      # decisión interna del motor
            "action": "REACTIVATE" | "IGNORE" | "PENDING" | "ERROR",
            "engine_output": dict  # resultado completo de run_unified_analysis
        }
    """
    symbol = signal.get("symbol")
    raw_direction = signal.get("direction", "long")

    logger.info("♻️ ApplicationLayer: evaluando reactivación %s (%s)", symbol, raw_direction)

    try:
        dir_hint = _norm_direction(raw_direction)

        engine_result: Dict[str, Any] = run_unified_analysis(
            symbol=symbol,
            direction_hint=dir_hint,
            context="reactivation",
            roi=None,
            loss_pct=None,
        )

        decision_block: Dict[str, Any] = engine_result.get("decision", {}) or {}
        decision = str(decision_block.get("decision", "wait"))
        allowed = bool(decision_block.get("allowed", False))

        # Mapeo de decisión técnica → acción del sistema
        if allowed and decision in {"reactivate", "enter", "proceed"}:
            action = "REACTIVATE"
        elif decision in {"skip", "block", "ignore"}:
            action = "IGNORE"
        elif decision in {"error"}:
            action = "ERROR"
        else:
            # wait, unknown, etc.
            action = "PENDING"

        return {
            "symbol": symbol,
            "direction": raw_direction,
            "decision": decision,
            "action": action,
            "engine_output": engine_result,
        }

    except Exception as e:
        logger.exception("❌ Error en evaluate_signal_reactivation(%s)", symbol)
        return {
            "symbol": symbol,
            "direction": raw_direction,
            "decision": "error",
            "action": "ERROR",
            "engine_output": {"error": str(e)},
        }


# ============================================================================
# 🟦 3) Evaluación de operaciones abiertas
# ============================================================================

async def evaluate_open_position(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa una posición abierta (no necesariamente en crisis).

    Espera un dict compatible con OperationTrackerAdapter._enrich_position():
        {
            "symbol": str,
            "side": "long"/"short",
            "size": float,
            "entry_price": float,
            "mark_price": float,
            "pnl": float,
            "roi": float,         # ROI % con apalancamiento
            "loss_pct": float,    # pérdida en %
            "raw": dict,          # posición original de Bybit
        }

    Devuelve:
        {
            "action": "hold" | "exit" | "reverse",
            "reason": str,
            "engine": dict,   # salida completa de run_unified_analysis
        }
    """
    symbol = position.get("symbol")
    side = position.get("side", "long")
    roi = position.get("roi")
    loss_pct = position.get("loss_pct")

    logger.info(
        "📡 ApplicationLayer: analizando posición abierta %s | side=%s | ROI=%.2f%% | loss=%.2f%%",
        symbol,
        side,
        float(roi) if roi is not None else 0.0,
        float(loss_pct) if loss_pct is not None else 0.0,
    )

    try:
        dir_hint = _norm_direction(side)

        engine_result: Dict[str, Any] = run_unified_analysis(
            symbol=symbol,
            direction_hint=dir_hint,
            context="operation",
            roi=roi,
            loss_pct=loss_pct,
        )

        decision_block: Dict[str, Any] = engine_result.get("decision", {}) or {}
        decision = str(decision_block.get("decision", "wait"))
        main_reason = _first_reason(decision_block.get("decision_reasons"))

        # Mapeo de decisión técnica → acción sobre la posición
        if decision in {"revert", "reverse"}:
            action = "reverse"
            reason = main_reason or "Motor sugiere reversión de la posición."
        elif decision in {"close", "exit"}:
            action = "exit"
            reason = main_reason or "Motor sugiere cerrar la posición."
        elif decision in {"skip", "block"}:
            action = "hold"
            reason = main_reason or "Condiciones no justifican cerrar ni revertir."
        else:
            # wait, unknown, hold, etc.
            action = "hold"
            reason = main_reason or "Motor en modo neutral, mantener de momento."

        return {
            "action": action,
            "reason": reason,
            "engine": engine_result,
        }

    except Exception as e:
        logger.exception("❌ Error en evaluate_open_position(%s)", symbol)
        return {
            "action": "hold",
            "reason": f"Error en motor técnico: {e}",
            "engine": {"error": str(e)},
        }


# ============================================================================
# 🟦 4) Evaluación en caso de STOP LOSS crítico (-50%)
# ============================================================================

async def evaluate_stoploss_reversal(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluación especial para casos de pérdida extrema
    (ej. ROI <= -50% o pérdida flotante muy alta).

    Recibe el mismo formato de posición que evaluate_open_position().
    """
    symbol = position.get("symbol")
    side = position.get("side", "long")
    roi = position.get("roi")
    loss_pct = position.get("loss_pct")

    logger.warning(
        "⚠️ Evaluación crítica (-50%%) para %s | side=%s | ROI=%.2f%% | loss=%.2f%%",
        symbol,
        side,
        float(roi) if roi is not None else 0.0,
        float(loss_pct) if loss_pct is not None else 0.0,
    )

    try:
        dir_hint = _norm_direction(side)

        # Para stops críticos usamos también el contexto "operation",
        # dejando que el motor aplique su lógica específica (ROI/loss).
        engine_result: Dict[str, Any] = run_unified_analysis(
            symbol=symbol,
            direction_hint=dir_hint,
            context="operation",
            roi=roi,
            loss_pct=loss_pct,
        )

        decision_block: Dict[str, Any] = engine_result.get("decision", {}) or {}
        decision = str(decision_block.get("decision", "wait"))
        main_reason = _first_reason(decision_block.get("decision_reasons"))

        if decision in {"revert", "reverse"}:
            action = "reverse"
            reason = main_reason or "Reversión detectada — mejor invertir la posición."
        elif decision in {"close", "exit", "block"}:
            action = "exit"
            reason = main_reason or "Condiciones malas → cerrar para limitar pérdidas."
        else:
            action = "hold"
            reason = main_reason or "Motor considera que aún puede recuperarse."

        return {
            "action": action,
            "reason": reason,
            "engine": engine_result,
        }

    except Exception as e:
        logger.exception("❌ Error en evaluate_stoploss_reversal(%s)", symbol)
        return {
            "action": "hold",
            "reason": f"Error en motor técnico durante evaluación crítica: {e}",
            "engine": {"error": str(e)},
        }
