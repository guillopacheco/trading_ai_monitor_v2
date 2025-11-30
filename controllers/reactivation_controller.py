"""
controllers/reactivation_controller.py
--------------------------------------
Controlador de reactivación de señales pendientes.

Flujo:
    scheduler_service.reactivation_loop()
        → run_reactivation_cycle()
        → db_service.get_pending_signals_for_reactivation()
        → core.signal_engine.analyze_reactivation()
        → db_service (marcar reactivada + log)
        → telegram_service.send_message()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

# Motor A+
try:
    from core.signal_engine import analyze_reactivation
except Exception:
    from signal_engine import analyze_reactivation  # type: ignore

# DB como módulo
try:
    import services.db_service as db_service  # type: ignore
except Exception:  # pragma: no cover
    db_service = None  # type: ignore

# Helpers
try:
    from utils.helpers import now_ts
except Exception:
    from datetime import datetime

    def now_ts() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")


logger = logging.getLogger("reactivation_controller")


# ============================================================
# 🔹 Utilidad interna para obtener pendientes
# ============================================================

def _fetch_pending_signals() -> List[Dict[str, Any]]:
    """
    Intenta recuperar señales pendientes desde db_service.

    Busca funciones en este orden:
        1) get_pending_signals_for_reactivation()
        2) get_pending_signals()
    """
    if db_service is None:
        logger.warning("⚠️ db_service no disponible; no se pueden leer señales pendientes.")
        return []

    try:
        if hasattr(db_service, "get_pending_signals_for_reactivation"):
            return db_service.get_pending_signals_for_reactivation()  # type: ignore
        if hasattr(db_service, "get_pending_signals"):
            return db_service.get_pending_signals()  # type: ignore
    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes desde DB: {e}")

    return []


def _mark_reactivated(signal_id: int, note: str = "") -> None:
    """
    Marca una señal como reactivada en DB si hay funciones disponibles.
    """
    if db_service is None:
        return

    try:
        if hasattr(db_service, "mark_signal_as_reactivated"):
            db_service.mark_signal_as_reactivated(signal_id, now_ts(), note)  # type: ignore
        elif hasattr(db_service, "update_signal_status"):
            db_service.update_signal_status(signal_id, "reactivated")  # type: ignore
        else:
            logger.debug("ℹ️ DB sin función específica para marcar reactivadas.")
    except Exception as e:
        logger.error(f"⚠️ No se pudo marcar señal {signal_id} como reactivada: {e}")


def _add_reactivation_log(signal_id: int, analysis: Dict[str, Any]) -> None:
    """
    Guarda un log del intento de reactivación, si db_service lo soporta.
    """
    if db_service is None:
        return

    try:
        if hasattr(db_service, "add_analysis_log"):
            db_service.add_analysis_log(  # type: ignore
                signal_id=signal_id,
                timestamp=now_ts(),
                result=analysis,
            )
    except Exception as e:
        logger.error(f"⚠️ No se pudo registrar log de reactivación: {e}")


# ============================================================
# 🔹 FUNCIÓN PÚBLICA: ciclo de reactivación
# ============================================================

async def run_reactivation_cycle() -> None:
    """
    Revisa todas las señales pendientes y decide cuáles reactivar.
    Llamada periódicamente por services/scheduler_service.py
    """
    logger.info("♻️ Revisando señales pendientes para reactivación…")

    pending = _fetch_pending_signals()
    if not pending:
        logger.info("📭 No hay señales pendientes para reactivar.")
        return

    logger.info(f"📊 {len(pending)} señal(es) pendientes encontradas.")

    reactivated_count = 0

    # Import local para evitar ciclos con telegram_service
    try:
        from services.telegram_service import send_message  # type: ignore
    except Exception:
        send_message = None  # type: ignore

    for sig in pending:
        signal_id = sig.get("id")
        symbol = sig.get("symbol")
        direction = sig.get("direction", "long")

        logger.info(f"♻️ Evaluando señal #{signal_id} → {symbol} ({direction})…")

        if not symbol or signal_id is None:
            logger.warning(f"⚠️ Señal inválida en DB: {sig}")
            continue

        try:
            result = await analyze_reactivation(symbol, direction)
        except Exception as e:
            logger.exception(f"❌ Error en analyze_reactivation para {symbol}: {e}")
            continue

        _add_reactivation_log(signal_id, result)

        reactivate = result.get("reactivate", False)
        grade = result.get("grade", "?")
        score = result.get("global_score", 0.0)

        if reactivate:
            reactivated_count += 1
            _mark_reactivated(
                signal_id,
                note=f"Reactivada con grade={grade}, score={score:.2f}",
            )

            # Mensaje amigable para el usuario
            text = (
                f"♻️ *Señal reactivada*\n"
                f"• Par: `{symbol}`\n"
                f"• Dirección original: *{direction.upper()}*\n"
                f"• Calificación: *{grade}*\n"
                f"• Score global: *{score:.2f}*\n\n"
                f"El motor técnico A+ considera que las condiciones actuales "
                f"vuelven a ser favorables para esta operación."
            )

            if send_message is not None:
                try:
                    await send_message(text)
                except Exception as e:
                    logger.error(f"❌ Error enviando mensaje de reactivación a Telegram: {e}")
        else:
            logger.info(
                f"⏳ Señal {symbol} (id={signal_id}) NO reactivada "
                f"(grade={grade}, score={score:.2f})."
            )

    logger.info(f"✅ Ciclo de reactivación completado. Reactivadas: {reactivated_count}.")
