"""
signal_controller.py
--------------------
Controlador maestro para manejar señales nuevas recibidas desde Telegram.

Funciones principales:
- Registrar señal en DB.
- Ejecutar motor técnico unificado.
- Guardar logs técnicos.
- Decidir si entrar, ignorar o dejar en seguimiento.
- Enviar notificaciones limpias y profesionales.

Dependencias:
- services.db_service
- services.bybit_service
- core.signal_engine
- notifier (o telegram_service en el futuro)
"""

import logging
from typing import Dict, Any

from services import db_service
from services.bybit_service import is_symbol_active
from core.signal_engine import analyze_signal
from notifier import send_message

logger = logging.getLogger("signal_controller")


# ============================================================
# 🔵 PROCESO PRINCIPAL AL RECIBIR UNA SEÑAL
# ============================================================
async def process_new_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orquesta todo el flujo para señales nuevas.

    Estructura esperada de `signal`:
    {
        "symbol": "BTCUSDT",
        "direction": "long",
        "entry": 42000.0,
        "tp_list": [...],
        "sl": 40100.0,
        ...
    }
    """

    symbol = signal.get("symbol")
    direction = signal.get("direction")

    logger.info(f"📩 Nueva señal recibida: {symbol} ({direction})")

    # ============================================================
    # 🔍 VALIDACIÓN BÁSICA
    # ============================================================
    if not symbol or not direction:
        logger.error("❌ Señal incompleta recibida.")
        return {"error": "Invalid signal"}

    # Validar que el símbolo exista en Bybit
    if not await is_symbol_active(symbol):
        msg = f"🚫 Señal {symbol}: No se pudo validar el mercado en Bybit."
        await send_message(msg)
        logger.warning(msg)
        return {"error": "symbol_inactive"}

    # ============================================================
    # 🗄 1. GUARDAR SEÑAL EN BASE DE DATOS
    # ============================================================
    signal_id = db_service.create_signal(signal)
    if signal_id is None:
        logger.error("❌ No se pudo guardar la señal en DB.")
        return {"error": "db_error"}

    logger.info(f"💾 Señal almacenada en DB con id={signal_id}")

    # ============================================================
    # 🧠 2. ANALIZAR SEÑAL CON EL MOTOR TÉCNICO
    # ============================================================
    analysis = await analyze_signal(symbol, direction)

    match_ratio = analysis.get("match_ratio", 0)
    decision = analysis.get("decision", "skip")
    grade = analysis.get("grade", "D")

    # ============================================================
    # 📝 3. GUARDAR LOG TÉCNICO
    # ============================================================
    db_service.add_analysis_log(
        signal_id=signal_id,
        match_ratio=match_ratio,
        recommendation=decision,
        details=analysis.get("details", ""),
    )

    db_service.set_signal_match_ratio(signal_id, match_ratio)

    # ============================================================
    # 🟩 4. DECISIÓN FINAL
    # ============================================================

    # --- Caso: entrada inmediata ---
    if decision == "enter":
        msg = _build_entry_message(signal, analysis)
        await send_message(msg)

        logger.info(f"🟢 Señal {symbol} APROBADA para entrada inmediata.")
        db_service.set_signal_reactivated(signal_id)  # estado = usable
        return {"id": signal_id, "status": "enter", "analysis": analysis}

    # --- Caso: condiciones mixtas → seguimiento ---
    if decision == "wait":
        msg = _build_followup_message(signal, analysis)
        await send_message(msg)

        logger.info(f"🟡 Señal {symbol} en seguimiento.")
        return {"id": signal_id, "status": "wait", "analysis": analysis}

    # --- Caso: no viable → ignorada ---
    if decision in ("skip", "reversal-risk"):
        msg = _build_reject_message(signal, analysis)
        await send_message(msg)

        db_service.set_signal_ignored(signal_id)
        logger.info(f"🔴 Señal {symbol} rechazada.")
        return {"id": signal_id, "status": "ignored", "analysis": analysis}

    # Si cae aquí, algo raro pasó
    logger.error(f"❌ Decisión inesperada del motor: {decision}")
    return {"id": signal_id, "status": "error", "analysis": analysis}


# ============================================================
# 🔵 MENSAJES PROFESIONALES
# ============================================================
def _build_entry_message(signal, analysis):
    return (
        f"🟢 **Entrada recomendada**\n\n"
        f"**Par:** {signal['symbol']}\n"
        f"**Dirección:** {signal['direction']}\n"
        f"**Match Ratio:** {analysis['match_ratio']}%\n"
        f"**Grado:** {analysis['grade']}\n\n"
        f"📊 *Todas las temporalidades están alineadas con la operación.*\n"
        f"El mercado muestra fuerza suficiente para validar la entrada."
    )


def _build_followup_message(signal, analysis):
    return (
        f"🟡 **Señal en seguimiento**\n\n"
        f"**Par:** {signal['symbol']}\n"
        f"**Dirección:** {signal['direction']}\n"
        f"**Match Ratio:** {analysis['match_ratio']}%\n"
        f"**Grado:** {analysis['grade']}\n\n"
        f"⏳ El mercado aún no muestra fuerza suficiente.\n"
        f"Se revisará automáticamente en las próximas actualizaciones."
    )


def _build_reject_message(signal, analysis):
    reason = (
        "Riesgo de reversión" if analysis["decision"] == "reversal-risk"
        else "Match insuficiente"
    )
    return (
        f"🔴 **Señal no viable en este momento**\n\n"
        f"**Par:** {signal['symbol']}\n"
        f"**Razón:** {reason}\n\n"
        f"📉 Match Ratio: {analysis['match_ratio']}%\n"
        f"**Grado:** {analysis['grade']}\n"
        f"⚠ Tendencias no alineadas o fuerza insuficiente.\n"
    )
