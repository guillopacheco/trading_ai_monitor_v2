"""
signal_reactivation_sync.py — versión final integrada con technical_brain
---------------------------------------------------------------------------
Reactiva señales cuando el mercado vuelve a alinear la tendencia con la señal original.

Criterio moderno de reactivación:
✔ allowed == True (motor técnico confirma coherencia)
✔ La tendencia mayor coincide con la dirección original
✔ No hay divergencias peligrosas
--------------------------------------------------------------------------- 
"""

import asyncio
import logging
from datetime import datetime

from config import SIGNAL_RECHECK_INTERVAL_MINUTES
from notifier import send_message
from technical_brain import analyze_market, format_market_report
from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
)

logger = logging.getLogger("signal_reactivation_sync")


# ============================================================
# ⚙️ Estado global para /estado
# ============================================================

reactivation_status = {
    "running": True,
    "last_run": None,
    "monitored_signals": 0,
    "reactivated_count": 0,
}

# ============================================================
# 🧠 Nueva lógica de reactivación
# ============================================================

def _can_reactivate(result: dict, original_dir: str) -> tuple[bool, str]:
    """
    Nuevo criterio basado en Technical Brain:

    ✔ allowed == True
    ✔ overall_trend coincide con dirección original
    ✔ divergencias NO peligrosas
    """

    # allowed=True → señal técnicamente válida
    if not result.get("allowed", False):
        return False, "Motor técnico no confirma entrada (allowed=False)."

    overall = (result.get("overall_trend") or "").lower()
    divs = result.get("divergences", {})
    dir_lower = original_dir.lower()

    # Coincidencia con tendencia mayor
    if dir_lower == "long" and "baj" in overall:
        return False, "La tendencia mayor sigue siendo BAJISTA."
    if dir_lower == "short" and "alc" in overall:
        return False, "La tendencia mayor sigue siendo ALCISTA."

    # Divergencias peligrosas
    rsi = (divs.get("RSI") or "").lower()
    macd = (divs.get("MACD") or "").lower()

    if dir_lower == "long" and ("bear" in rsi or "bear" in macd):
        return False, "Divergencias bajistas detectadas."
    if dir_lower == "short" and ("bull" in rsi or "bull" in macd):
        return False, "Divergencias alcistas detectadas."

    return True, "Condiciones ideales para reactivar."


# ============================================================
# 📨 Mensaje final
# ============================================================

def _build_reactivation_message(signal: dict, result: dict) -> str:
    symbol = signal.get("symbol", "N/A")
    direction = signal.get("direction", "long").upper()
    lev = signal.get("leverage", 20)
    entry = signal.get("entry_price")
    created = signal.get("created_at", "N/A")

    header = (
        f"♻️ *Señal reactivada: {symbol}*\n"
        f"📌 Dirección original: *{direction}* x{lev}\n"
        f"💰 Entry original: {entry}\n"
        f"🕒 Señal enviada: {created}\n\n"
    )

    return header + format_market_report(result)


# ============================================================
# 🔁 Ciclo de reactivación — UNA PASADA
# ============================================================

async def run_reactivation_cycle() -> dict:
    logger.info("♻️ Ejecutando ciclo de reactivación…")

    stats = {"checked": 0, "reactivated": 0}

    try:
        signals = get_pending_signals_for_reactivation()
    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes: {e}")
        return stats

    reactivation_status["monitored_signals"] = len(signals)
    reactivation_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not signals:
        logger.info("ℹ️ No hay señales para revisar.")
        return stats

    for sig in signals:
        stats["checked"] += 1

        try:
            symbol = sig["symbol"]
            direction = sig["direction"]
            lev = int(sig.get("leverage", 20))

            logger.info(f"🔎 Revisando {symbol} ({direction} x{lev})…")

            # 1) Reanálisis técnico completo
            result = analyze_market(symbol, direction_hint=direction)

            # 2) Decidir reactivación
            allowed, reason = _can_reactivate(result, direction)

            if not allowed:
                logger.info(f"⏳ {symbol}: descartada — {reason}")
                continue

            # 3) Marcar en DB
            mark_signal_reactivated(sig["id"])
            stats["reactivated"] += 1
            reactivation_status["reactivated_count"] += 1

            # 4) Enviar mensaje
            msg = _build_reactivation_message(sig, result)
            await send_message(msg)

            logger.info(f"🟢 {symbol} reactivada correctamente.")

        except Exception as e:
            logger.error(f"❌ Error revisando {sig}: {e}")

    return stats


# ============================================================
# 🔁 Bucle automático
# ============================================================

async def reactivation_loop():
    logger.info("♻️ Iniciando monitoreo automático de reactivaciones…")

    while True:
        try:
            await run_reactivation_cycle()
        except Exception as e:
            logger.error(f"❌ Error en reactivation_loop: {e}")

        logger.info(
            f"🕒 Próxima revisión en {SIGNAL_RECHECK_INTERVAL_MINUTES} minutos."
        )
        await asyncio.sleep(SIGNAL_RECHECK_INTERVAL_MINUTES * 60)


# ============================================================
# API para /estado y compatibilidad
# ============================================================

def get_reactivation_status():
    return reactivation_status.copy()


async def auto_reactivation_loop(interval_seconds=None):
    await reactivation_loop()
