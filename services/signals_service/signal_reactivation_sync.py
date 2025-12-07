"""
signal_reactivation_sync.py
---------------------------

Servicio de reactivación de señales usando el *motor técnico unificado*
(technical_engine.analyze).

✅ Objetivos de esta versión (Opción C, Fase 1.2)
    - Usar **UN SOLO motor técnico** para decidir reactivaciones.
    - Respetar los mismos criterios de decisión que /analizar.
    - Mantener la lógica simple y estable (sin wrappers intermedios).
    - Permitir uso tanto automático (daemon) como manual (/reactivacion).

API pública:
    - start_reactivation_monitor()  -> bucle en segundo plano (main.py)
    - run_reactivation_cycle()      -> ciclo único, usado por /reactivacion
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

# Usamos directamente el motor técnico unificado
from services.technical_engine.technical_engine import analyze as engine_analyze


logger = logging.getLogger("signal_reactivation_sync")

# Intervalo de reactivación automática (segundos)
REACTIVATION_INTERVAL = 60


# ============================================================
# Utilidades internas
# ============================================================

def _normalize_direction(raw_direction: str) -> str:
    """
    Normaliza la dirección de la señal a 'long' o 'short'.
    Acepta variantes como 'buy', 'sell', 'Long📈', 'Short📉', etc.
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
    Evita errores tipo `'str' object has no attribute 'get'`.
    """
    try:
        data = engine_analyze(
            symbol=symbol,
            direction_hint=direction,
            context=context,
            roi=None,
            loss_pct=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("❌ Error llamando al motor técnico para %s: %s", symbol, exc)
        return {
            "allowed": False,
            "decision": "error",
            "decision_reasons": [f"Error en motor técnico: {exc}"],
            "technical_score": 0.0,
            "match_ratio": 0.0,
            "grade": "D",
            "confidence": 0.0,
            "context": context,
        }

    if isinstance(data, dict):
        return data

    # Cualquier cosa que no sea dict se envuelve en un dict estándar
    logger.error(
        "❌ Motor técnico devolvió tipo inesperado (%s) para %s: %r",
        type(data),
        symbol,
        data,
    )
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
    """Devuelve el primer motivo legible desde decision_reasons."""
    if isinstance(decision_reasons, list) and decision_reasons:
        return str(decision_reasons[0])
    if isinstance(decision_reasons, str):
        return decision_reasons
    return "Sin motivo detallado."


async def _process_single_signal(signal: Dict[str, Any], manual: bool = False) -> Dict[str, Any]:
    """
    Procesa una única señal pendiente de reactivación usando el motor técnico.

    Devuelve un pequeño resumen estructurado que luego se usa para:
        - logging
        - respuesta a /reactivacion
    """
    symbol = signal["symbol"]
    raw_direction = signal.get("direction", "long")
    direction = _normalize_direction(raw_direction)

    logger.info("♻️ Revisando señal pendiente: %s (%s).", symbol, direction)

    # 1) Ejecutar análisis técnico unificado en contexto de reactivación
    result = _safe_engine_call(symbol, direction, context="reactivation")

    decision = result.get("decision", "wait")
    allowed = bool(result.get("allowed", False))
    match_ratio = result.get("match_ratio")
    tech_score = result.get("technical_score")
    grade = result.get("grade")
    confidence = result.get("confidence")
    main_reason = _extract_main_reason(result.get("decision_reasons"))

    # 2) Guardar log de análisis en DB (para auditoría / histórico)
    try:
        save_analysis_log(
            symbol=symbol,
            context="reactivation",
            direction=direction,
            engine_decision=decision,
            engine_allowed=1 if allowed else 0,
            grade=grade or "",
            match_ratio=float(match_ratio) if match_ratio is not None else None,
            technical_score=float(tech_score) if tech_score is not None else None,
            extra=result,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("⚠️ No se pudo guardar el log de análisis para %s: %s", symbol, exc)

    # 3) Actualizar estado de la señal según decisión del motor
    signal_id = signal["id"]
    status_msg: str

    if allowed and decision == "reactivate":
        # Señal considerada apta para reactivarse
        mark_signal_reactivated(
            signal_id=signal_id,
            status="reactivated",
            reason=f"reactivated_by_engine: {main_reason}",
        )
        status_msg = "reactivated"
        logger.info(
            "✅ Señal %s REACTIVADA por motor único (grade=%s, score=%s, match=%s).",
            symbol,
            grade,
            tech_score,
            match_ratio,
        )

    elif decision in {"skip", "block", "ignore"}:
        # El motor considera que NO debe reactivarse
        mark_signal_reactivated(
            signal_id=signal_id,
            status="cancelled",
            reason=f"blocked_by_engine: {main_reason}",
        )
        status_msg = "cancelled"
        logger.info(
            "⛔ Señal %s descartada por motor único (%s).",
            symbol,
            main_reason,
        )

    elif decision == "error":
        # Error técnico → no cambiamos estado, solo registramos
        status_msg = "error"
        logger.warning(
            "⚠️ Señal %s no modificada por error del motor: %s",
            symbol,
            main_reason,
        )

    else:
        # Caso 'wait' u otras decisiones neutrales:
        # La señal sigue pendiente para futuras revisiones.
        status_msg = "pending"
        logger.info(
            "⏳ Señal %s permanece PENDIENTE (decision=%s, grade=%s, score=%s, match=%s).",
            symbol,
            decision,
            grade,
            tech_score,
            match_ratio,
        )

    # 4) Resumen compacto para consumo de /reactivacion
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
# Ciclo público — llamado desde command_bot (/reactivacion)
# ============================================================

async def run_reactivation_cycle() -> str:
    """
    Ejecuta **un ciclo** de reactivación:

        1) Lee señales pendientes de la DB.
        2) Las analiza con el motor técnico.
        3) Actualiza su estado (reactivated / cancelled / pending).
        4) Devuelve un resumen legible para Telegram.

    Usado por:
        - comando /reactivacion
        - monitor automático en segundo plano
    """
    pending: List[Dict[str, Any]] = get_pending_signals_for_reactivation(limit=20)

    if not pending:
        logger.info("♻️ No hay señales pendientes para reactivación.")
        return "✅ No hay señales pendientes para reactivación."

    summaries: List[Dict[str, Any]] = []
    for signal in pending:
        summary = await _process_single_signal(signal, manual=True)
        summaries.append(summary)

    # Construir respuesta amigable para el bot de comandos
    lines = ["♻️ Reactivación completada:"]
    for s in summaries:
        emoji = "✅" if s["status"] == "reactivated" else "⛔" if s["status"] == "cancelled" else "⏳"
        lines.append(
            f"{emoji} {s['symbol']} ({s['direction']}) → {s['decision']} "
            f"[{s.get('grade','-')}, score={s.get('technical_score')}, match={s.get('match_ratio')}]"
            f"\n   ↳ {s['reason']}"
        )

    return "\n".join(lines)


# ============================================================
# Monitor automático — usado por main.py
# ============================================================

async def start_reactivation_monitor() -> None:
    """
    Bucle en segundo plano que revisa periódicamente las señales pendientes.

    Llamado desde main.py como tarea asíncrona:
        reactivation_task = asyncio.create_task(start_reactivation_monitor())
    """
    logger.info("♻️ Monitor de reactivación automática iniciado (intervalo=%ss).", REACTIVATION_INTERVAL)

    while True:
        try:
            await run_reactivation_cycle()
        except Exception as exc:  # noqa: BLE001
            logger.exception("❌ Error en ciclo de reactivación automática: %s", exc)

        await asyncio.sleep(REACTIVATION_INTERVAL)
