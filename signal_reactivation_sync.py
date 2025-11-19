"""
signal_reactivation_sync.py — versión final integrada con trend_system_final
---------------------------------------------------------------------------
Reactiva señales cuando el mercado vuelve a alinearse con la señal original.

Criterio moderno de reactivación:
✔ match_ratio ≥ threshold["reactivation"]
✔ recomendación positiva del motor técnico
✔ divergencias no peligrosas
✔ sesgo smart compatible con la dirección original
---------------------------------------------------------------------------
"""

import asyncio
import logging
from datetime import datetime

from config import SIGNAL_RECHECK_INTERVAL_MINUTES
from notifier import send_message
from database import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    save_analysis_log,
)

from trend_system_final import (
    analyze_and_format,
    analyze_trend_core,
    _get_thresholds,
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


# ============================================================
# 🧠 Criterio de reactivación basado en trend_system_final
# ============================================================

def _can_reactivate(result: dict, original_dir: str) -> tuple[bool, str]:
    """
    Política moderna de reactivación:

    ✔ match_ratio ≥ threshold
    ✔ divergencias no peligrosas
    ✔ sesgo smart compatible

    No usamos "allowed" ni "overall_trend" en español.
    """
    thresholds = _get_thresholds()
    needed = thresholds.get("reactivation", 80.0)

    match_ratio = result.get("match_ratio", 0.0)
    if match_ratio < needed:
        return False, f"Match ratio insuficiente ({match_ratio:.1f}% < {needed}%)."

    # Divergencias
    divs = result.get("divergences", {})
    rsi = (divs.get("RSI") or "").lower()
    macd = (divs.get("MACD") or "").lower()

    dir_lower = original_dir.lower()

    # Divergencias contrarias a la dirección
    if dir_lower == "long":
        if "baj" in rsi or "baj" in macd or "bear" in rsi or "bear" in macd:
            return False, "Divergencias bajistas detectadas."
    else:  # short
        if "alc" in rsi or "alc" in macd or "bull" in rsi or "bull" in macd:
            return False, "Divergencias alcistas detectadas."

    # Smart bias
    smart_bias = result.get("smart_bias", "").lower()
    if dir_lower == "long" and "bear" in smart_bias:
        return False, "Smart bias bajista."
    if dir_lower == "short" and "bull" in smart_bias:
        return False, "Smart bias alcista."

    return True, "Condiciones ideales para reactivar."


# ============================================================
# 📨 Construcción del mensaje final
# ============================================================

def _build_reactivation_message(signal: dict, result: dict, formatted: str) -> str:
    symbol = signal.get("symbol", "N/A")
    direction = signal.get("direction", "long").upper()
    entry = signal.get("entry_price")
    lev = signal.get("leverage", 20)
    created = signal.get("created_at", "N/A")

    header = (
        f"♻️ *Señal reactivada: {symbol}*\n"
        f"📌 Dirección original: *{direction}* x{lev}\n"
        f"💰 Entry original: `{entry}`\n"
        f"🕒 Señal enviada: {created}\n\n"
    )

    return header + formatted


# ============================================================
# 🔁 Ejecución de un ciclo completo
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
        logger.info("ℹ️ No hay señales pendientes para revisar.")
        return stats

    for sig in signals:
        stats["checked"] += 1

        try:
            symbol = sig["symbol"]
            direction = sig["direction"]

            logger.info(f"🔎 Revisando {symbol} ({direction})…")

            # 1) Análisis técnico completo (sin formato)
            result = analyze_trend_core(symbol, direction_hint=direction)

            # 2) Criterio de reactivación
            allowed, reason = _can_reactivate(result, direction)
            if not allowed:
                logger.info(f"⏳ {symbol}: descartada — {reason}")
                continue

            # 3) Generar análisis formateado para Telegram
            _, formatted = analyze_and_format(symbol, direction_hint=direction)

            # 4) Guardar análisis en el log
            save_analysis_log(
                signal_id=sig["id"],
                match_ratio=result.get("match_ratio", 0.0),
                recommendation=result.get("recommendation", ""),
                details=f"Reactivación automática\n{formatted}",
            )

            # 5) Marcar en BD
            mark_signal_reactivated(sig["id"])
            stats["reactivated"] += 1
            reactivation_status["reactivated_count"] += 1

            # 6) Enviar mensaje al usuario (to_thread por ser sync)
            msg = _build_reactivation_message(sig, result, formatted)
            await asyncio.to_thread(send_message, msg)

            logger.info(f"🟢 {symbol} reactivada correctamente.")

        except Exception as e:
            logger.error(f"❌ Error revisando {sig}: {e}")

    return stats


# ============================================================
# 🔁 Bucle automático continuo
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
# API pública
# ============================================================

def get_reactivation_status():
    return reactivation_status.copy()


async def auto_reactivation_loop(interval_seconds=None):
    await reactivation_loop()
