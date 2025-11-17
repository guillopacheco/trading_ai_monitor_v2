"""
signal_reactivation_sync.py
------------------------------------------------------------
Sistema robusto de reactivación de señales basado en:

✔ tendencia mayor (30m–1h–4h)
✔ match técnico real ≥ 80%
✔ coherencia con el motor trend_system_final
✔ bloqueo por divergencias peligrosas
✔ mensajes unificados
------------------------------------------------------------
"""

import asyncio
import logging
from datetime import datetime

from trend_system_final import analyze_and_format, _get_thresholds
from notifier import send_message
from config import SIGNAL_RECHECK_INTERVAL_MINUTES

from signal_manager_db import (
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
)


logger = logging.getLogger("signal_reactivation_sync")

# =====================================================================
# 🔐 Reglas avanzadas de seguridad (anti-reversal)
# =====================================================================
def _passes_major_trend_filter(result: dict, direction: str) -> bool:
    """
    Filtra casos donde el 5m–15m se ven bien pero 1h o 4h muestran reversión.
    (caso clásico de falsa reactivación)
    """

    major = (result.get("major_trend") or "").lower()

    if direction == "long" and "bajista" in major:
        return False

    if direction == "short" and "alcista" in major:
        return False

    return True


def _passes_divergence_filter(result: dict, direction: str) -> bool:
    """
    Bloquea reactivaciones en caso de divergencias peligrosas.
    """

    divs = result.get("divergences", {})

    # Divergencias simples
    rsi_div = (divs.get("RSI") or "").lower()
    macd_div = (divs.get("MACD") or "").lower()

    # smart divergence
    smart_bias = (result.get("smart_bias") or "").lower()

    # LONG → divergencia bajista detectada
    if direction == "long":
        if "bear" in rsi_div or "bear" in macd_div:
            return False
        if "bearish" in smart_bias:
            return False

    # SHORT → divergencia alcista detectada
    if direction == "short":
        if "bull" in rsi_div or "bull" in macd_div:
            return False
        if "bullish" in smart_bias:
            return False

    return True

def _passes_match_filter(result: dict) -> bool:
    """
    Condición mínima basada en umbral dinámico:
    - match_ratio ≥ umbral dinámico (agresivo/conservador)
    - recomendación debe comenzar con 'Señal confirmada'
    """
    match_ratio = result.get("match_ratio", 0.0)
    rec = (result.get("recommendation") or "").lower()

    # Leer umbral dinámico desde trend_system_final
    th = _get_thresholds()
    needed = th.get("reactivation", 80.0)

    return match_ratio >= needed and rec.startswith("✅ señal confirmada")

# =====================================================================
# 🧠 Inspección completa de reactivación
# =====================================================================
def _reactivation_allowed(result: dict, direction: str) -> tuple[bool, str]:
    """
    Evalúa todos los filtros de seguridad.
    Devuelve (permitido:bool, motivo:str)
    """

    if not _passes_match_filter(result):
        return False, "Match técnico insuficiente (<80%)"

    if not _passes_major_trend_filter(result, direction):
        return False, "Tendencia mayor contradictoria (1h/4h)"

    if not _passes_divergence_filter(result, direction):
        return False, "Divergencias fuertes en contra"

    return True, "Condiciones óptimas"

# =====================================================================
# 📨 Mensaje final — unificado y profesional
# =====================================================================
def _build_reactivation_message(result: dict, formatted_report: str) -> str:
    symbol = result.get("symbol", "N/A")
    direction = result.get("direction_hint", "").upper()
    match_ratio = result.get("match_ratio", 0.0)

    header = (
        f"♻️ *Reactivación detectada: {symbol}*\n"
        f"📌 *Dirección:* {direction}\n"
        f"⚙️ *Match técnico:* {match_ratio:.1f}%\n"
        f"✨ *La señal ha sido reactivada antes del Entry original.*\n\n"
    )

    return header + formatted_report

# =====================================================================
# 🔍 Revisión individual — usada por el bot (cmd /reactivacion)
# =====================================================================
def check_reactivation(symbol: str, direction: str, leverage: int, entry_price: float):
    """
    Ejecuta una sola revisión de reactivación.
    Puede ser llamada desde /reactivacion (manual) o desde el loop.
    """
    try:
        result, formatted = analyze_and_format(symbol, direction_hint=direction)

        allowed, reason = _reactivation_allowed(result, direction)

        return {
            "symbol": symbol,
            "allowed": allowed,
            "reason": reason,
            "result": result,
            "formatted": formatted,
        }
    except Exception as e:
        logger.error(f"❌ Error en check_reactivation para {symbol}: {e}")
        return None

# =====================================================================
# 🔁 Bucle automático de reactivación
# =====================================================================
reactivation_status = {
    "running": True,
    "last_run": None,
    "monitored_signals": 0,
}

async def reactivation_loop():
    """
    Bucle infinito que revisa señales pendientes cada N minutos.
    """
    global reactivation_status

    logger.info("♻️ Iniciando monitoreo automático de reactivaciones...")

    while True:
        try:
            signals = get_pending_signals_for_reactivation()
            reactivation_status["monitored_signals"] = len(signals)
            reactivation_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not signals:
                logger.info("ℹ️ No hay señales pendientes para revisar.")
            else:
                for sig in signals:
                    symbol = sig["symbol"]
                    direction = sig["direction"]
                    sig_id = sig["id"]

                    logger.info(f"🔎 Revisando {symbol} ({direction}) para reactivación...")

                    # 1) Ejecutar análisis completo
                    result, formatted = analyze_and_format(symbol, direction_hint=direction)

                    # 2) Validar con todos los filtros
                    allowed, reason = _reactivation_allowed(result, direction)

                    if allowed:
                        logger.info(f"🟢 Reactivación válida para {symbol}: {result['match_ratio']}%")

                        # Guardar en DB
                        mark_signal_reactivated(sig_id)

                        # Construir y enviar mensaje final
                        msg = _build_reactivation_message(result, formatted)
                        await send_message(msg)

                    else:
                        logger.info(
                            f"⏳ {symbol}: reactivación descartada — {reason} "
                            f"({result['match_ratio']}%)"
                        )

            # esperar siguiente ciclo
            logger.info(f"🕒 Próxima revisión en {SIGNAL_RECHECK_INTERVAL_MINUTES} minutos.")
            await asyncio.sleep(SIGNAL_RECHECK_INTERVAL_MINUTES * 60)

        except Exception as e:
            logger.error(f"❌ Error en reactivation_loop: {e}")
            await asyncio.sleep(10)

# =====================================================================
# 🛈 API para command_bot.py (/estado)
# =====================================================================
def get_reactivation_status():
    return reactivation_status.copy()
