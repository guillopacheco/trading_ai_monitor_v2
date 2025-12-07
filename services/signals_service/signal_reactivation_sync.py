"""
signal_reactivation_sync.py
---------------------------

Servicio de reactivación de señales usando el motor técnico unificado.

Fase 1.2 (Opción C) — versión corregida con parches 2025-12-07:
    ✔ Fix: remove non-existent parameter "limit" from DB call
    ✔ Fix: save_analysis_log signature corrected to match database.py
    ✔ Lógica estable, limpia y lista para la arquitectura hexagonal
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, List

from core.database import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    save_analysis_log,
)

# Motor técnico unificado (technical_engine.analyze)
from services.technical_engine.technical_engine import analyze as engine_analyze

logger = logging.getLogger("signal_reactivation_sync")

# Intervalo de reactivación automática (segundos)
REACTIVATION_INTERVAL = 60


# ============================================================
# Utilidades internas
# ============================================================

def _normalize_direction(raw_direction: str) -> str:
    """
    Normaliza la dirección a long/short.
    """
    if not raw_direction:
        return "long"

    d = raw_direction.strip().lower()
    if "short" in d or "sell" in d:
        return "short"
    return "long"


def _safe_engine_call(symbol: str, direction: str, context: str) -> Dict[str, Any]:
    """
    Llama al motor técnico unificado y garantiza siempre un dict.
    """
    try:
        data = engine_analyze(
            symbol=symbol,
            direction_hint=direction,
            context=context,
            roi=None,
            loss_pct=None,
        )
    except Exception as exc:
        logger.exception("❌ Error llamando al motor técnico para %s: %s", symbol, exc)
        return {
            "allowed": False,
            "decision": "error",
            "decision_reasons": [f"Error motor técnico: {exc}"],
            "technical_score": 0.0,
            "match_ratio": 0.0,
            "grade": "D",
            "confidence": 0.0,
            "context": context,
        }

    if isinstance(data, dict):
        return data

    logger.error("❌ Motor técnico devolvió tipo inesperado (%s) para %s: %r",
                 type(data), symbol, data)
    return {
        "allowed": False,
        "decision": "error",
        "decision_reasons": [f"Respuesta inesperada del motor: {data!r}"],
        "technical_score": 0.0,
        "match_ratio": 0.0,
        "grade": "D",
        "confidence": 0.0,
        "context": context,
    }


def _extract_main_reason(decision_reasons: Any) -> str:
    """Devuelve el primer motivo legible."""
    if isinstance(decision_reasons, list) and decision_reasons:
        return str(decision_reasons[0])
    if isinstance(decision_reasons, str):
        return decision_reasons
    return "Sin motivo detallado."


# ============================================================
# Proceso interno de una señal
# ============================================================

async def _process_single_signal(signal: Dict[str, Any], manual: bool = False) -> Dict[str, Any]:
    symbol = signal["symbol"]
    raw_direction = signal.get("direction", "long")
    direction = _normalize_direction(raw_direction)

    logger.info("♻️ Revisando señal pendiente: %s (%s).", symbol, direction)

    # 1) Ejecutar motor técnico unificado
    result = _safe_engine_call(symbol, direction, context="reactivation")

    decision = result.get("decision", "wait")
    allowed = bool(result.get("allowed", False))
    match_ratio = result.get("match_ratio")
    tech_score = result.get("technical_score")
    grade = result.get("grade")
    confidence = result.get("confidence")
    main_reason = _extract_main_reason(result.get("decision_reasons"))

    # 2) Guardar log en DB — FIRMA CORRECTA SEGÚN database.py
    try:
        save_analysis_log(
            signal_id=signal["id"],
            match_ratio=float(match_ratio) if match_ratio is not None else 0.0,
            recommendation=decision,
            details=str(result),         # Guardamos snapshot completo del motor
        )
    except Exception as exc:
        logger.exception("⚠️ No se pudo guardar log para %s: %s", symbol, exc)

    # 3) Actualizar estado según decisión
    signal_id = signal["id"]
    status_msg: str

    if allowed and decision == "reactivate":
        # Señal apta para reactivarse
        mark_signal_reactivated(signal_id)
        status_msg = "reactivated"
        logger.info("✅ Señal %s REACTIVADA (grade=%s, score=%s, match=%s).",
                    symbol, grade, tech_score, match_ratio)

    elif decision in {"skip", "block", "ignore"}:
        # NO reactivar
        logger.info("⛔ Señal %s descartada (%s).", symbol, main_reason)
        status_msg = "cancelled"

    elif decision == "error":
        # Error técnico → no cambiar estado
        status_msg = "error"
        logger.warning("⚠️ Señal %s no modificada por error del motor: %s",
                       symbol, main_reason)

    else:
        # Caso pendings → se revisará de nuevo en el futuro
        status_msg = "pending"
        logger.info("⏳ Señal %s permanece PENDIENTE (decision=%s, score=%s).",
                    symbol, decision, tech_score)

    # Resumen compacto para /reactivacion
    summary = {
        "symbol": symbol,
        "direction": direction,
        "decision": decision,
        "allowed": allowed,
        "status": status_msg,
        "grade": grade,
        "confidence": confidence,
        "match_ratio": match_ratio,
        "technical_score": tech_score,
        "reason": main_reason,
    }

    return summary


# ============================================================
# Ciclo público — usado por /reactivacion y el demonio automático
# ============================================================

async def run_reactivation_cycle() -> str:
    """
    Ejecuta un ciclo único de reactivación de señales.
    """
    pending: List[Dict[str, Any]] = get_pending_signals_for_reactivation()  # FIX: sin "limit"

    if not pending:
        logger.info("♻️ No hay señales pendientes.")
        return "✅ No hay señales pendientes para reactivación."

    summaries: List[Dict[str, Any]] = []

    for signal in pending:
        summary = await _process_single_signal(signal, manual=True)
        summaries.append(summary)

    # Construir mensaje limpio para Telegram
    lines = ["♻️ *Resumen de reactivación:*"]
    for s in summaries:
        lines.append(
            f"• {s['symbol']} ({s['direction']}) → "
            f"{s['status']} — {s['reason']}"
        )

    return "\n".join(lines)


# ============================================================
# Monitor automático (background)
# ============================================================

async def start_reactivation_monitor() -> None:
    """
    Bucle infinito de reactivación automática cada REACTIVATION_INTERVAL segundos.
    """
    logger.info(f"♻️ Monitor de reactivación automática iniciado (intervalo={REACTIVATION_INTERVAL}s).")

    while True:
        try:
            await run_reactivation_cycle()
        except Exception as exc:
            logger.exception("❌ Error en ciclo de reactivación automática: %s", exc)

        await asyncio.sleep(REACTIVATION_INTERVAL)
