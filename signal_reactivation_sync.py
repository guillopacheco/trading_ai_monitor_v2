"""
signal_reactivation_sync.py
------------------------------------------------------------
Sistema de reactivación de señales usando technical_brain.

- Revisa periódicamente la tabla `signals` (estado 'pending' o similar)
- Recalcula el análisis técnico con `technical_brain.analyze_symbol`
- Si el match técnico es alto (>= umbral), marca la señal como reactivada
- Envía un reporte limpio por Telegram

Usa:
- technical_brain.analyze_symbol, format_analysis_for_telegram
- signal_manager_db.get_pending_signals_for_reactivation, mark_signal_reactivated
- config.SIGNAL_RECHECK_INTERVAL_MINUTES
------------------------------------------------------------
"""

import asyncio
import logging
from datetime import datetime

from config import SIGNAL_RECHECK_INTERVAL_MINUTES
from notifier import send_message
from technical_brain import analyze_symbol, format_analysis_for_telegram
from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
)

logger = logging.getLogger("signal_reactivation_sync")

# ============================================================
# ⚙️ Estado global (para /estado)
# ============================================================

reactivation_status = {
    "running": True,
    "last_run": None,
    "monitored_signals": 0,
    "reactivated_count": 0,
}

# Umbral básico de match técnico para reactivar
MIN_REACTIVATION_MATCH = 80.0


# ============================================================
# 🧠 Lógica de filtrado de reactivación
# ============================================================

def _can_reactivate(result: dict) -> tuple[bool, str]:
    """
    Decide si una señal puede considerarse reactivada.

    Usa:
    - summary['match_ratio'] (0–100)
    - summary['recommendation'] (texto)
    """
    summary = result.get("summary", {}) or {}
    match_ratio = float(summary.get("match_ratio", 0.0) or 0.0)
    recommendation = (summary.get("recommendation") or "").lower()

    if match_ratio < MIN_REACTIVATION_MATCH:
        return False, f"Match técnico insuficiente ({match_ratio:.1f}%)"

    # Si la recomendación suena claramente negativa, no reactivar
    if any(word in recommendation for word in ["descartar", "evitar", "no entrar"]):
        return False, f"Recomendación desfavorable: {recommendation[:40]}..."

    return True, f"Match técnico adecuado ({match_ratio:.1f}%)"


def _build_reactivation_message(signal: dict, result: dict) -> str:
    """
    Construye el mensaje final de reactivación para Telegram.
    """
    symbol = signal.get("symbol", "N/A")
    direction = signal.get("direction", "long").upper()
    lev = signal.get("leverage", 20)
    entry_price = signal.get("entry_price")
    created_at = signal.get("created_at", "N/A")

    summary = result.get("summary", {}) or {}
    match_ratio = float(summary.get("match_ratio", 0.0) or 0.0)

    header = (
        f"♻️ *Señal reactivada: {symbol}*\n"
        f"📌 Dirección original: *{direction}* x{lev}\n"
        f"💰 Entry original: {entry_price}\n"
        f"🕒 Señal original: {created_at}\n"
        f"⚙️ Match técnico actual: *{match_ratio:.1f}%*\n\n"
    )

    body = format_analysis_for_telegram(result)

    return header + body


# ============================================================
# 🔁 Ciclo de reactivación (una pasada)
# ============================================================

async def run_reactivation_cycle() -> dict:
    """
    Ejecuta UNA pasada de revisión de señales pendientes.

    Devuelve:
        {
            "checked": N,
            "reactivated": M
        }
    """
    logger.info("♻️ Ejecutando ciclo de reactivación de señales...")

    stats = {"checked": 0, "reactivated": 0}

    try:
        signals = get_pending_signals_for_reactivation()
    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes: {e}")
        return stats

    reactivation_status["monitored_signals"] = len(signals)
    reactivation_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not signals:
        logger.info("ℹ️ No hay señales pendientes para revisar.")
        return stats

    for sig in signals:
        try:
            stats["checked"] += 1

            symbol = sig.get("symbol")
            direction = sig.get("direction", "long")
            leverage = int(sig.get("leverage", 20))

            if not symbol:
                logger.warning(f"⚠️ Señal sin símbolo válido: {sig}")
                continue

            logger.info(
                f"🔎 Revisando {symbol} ({direction.upper()} x{leverage}) "
                f"para posible reactivación..."
            )

            # 1) Recalcular análisis completo
            result = analyze_symbol(symbol, direction_hint=direction, leverage=leverage)

            # 2) Decidir si se reactiva
            allowed, reason = _can_reactivate(result)

            if not allowed:
                logger.info(
                    f"⏳ {symbol}: reactivación descartada — {reason}"
                )
                continue

            # 3) Marcar en DB
            signal_id = sig.get("id")
            if signal_id is not None:
                mark_signal_reactivated(signal_id)

            stats["reactivated"] += 1
            reactivation_status["reactivated_count"] += 1

            # 4) Enviar mensaje final
            msg = _build_reactivation_message(sig, result)
            await send_message(msg)

            logger.info(
                f"🟢 Señal {symbol} reactivada correctamente "
                f"({result.get('summary', {}).get('match_ratio', 0):.1f}%)"
            )

        except Exception as e:
            logger.error(f"❌ Error revisando señal {sig}: {e}")

    return stats


# ============================================================
# 🔁 Bucle automático (usado por main.py)
# ============================================================

async def reactivation_loop():
    """
    Bucle infinito que corre `run_reactivation_cycle()` cada N minutos.
    """
    logger.info("♻️ Iniciando monitoreo automático de reactivaciones...")

    while True:
        try:
            await run_reactivation_cycle()
        except Exception as e:
            logger.error(f"❌ Error en reactivation_loop: {e}")

        logger.info(f"🕒 Próxima revisión en {SIGNAL_RECHECK_INTERVAL_MINUTES} minutos.")
        await asyncio.sleep(SIGNAL_RECHECK_INTERVAL_MINUTES * 60)


# ============================================================
# 🛈 API para /estado y compatibilidad
# ============================================================

def get_reactivation_status():
    return reactivation_status.copy()


async def auto_reactivation_loop(interval_seconds: int | None = None):
    """
    Wrapper para mantener compatibilidad con main.py:
    main.py llama: asyncio.create_task(auto_reactivation_loop(900))
    El parámetro interval_seconds se ignora; se usa config.
    """
    await reactivation_loop()
