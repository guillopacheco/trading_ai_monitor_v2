"""
signal_reactivation_sync.py
------------------------------------------------------------
Versión sincronizada con el ecosistema actual:
- indicators.py (get_technical_data)
- trend_system_final.py (analyze_and_format)
- notifier.py (send_message)
- database.py (get_signals, update_operation_status)

Detecta si una señal descartada o en espera vuelve a alinearse
con la tendencia técnica y reactiva la oportunidad automáticamente.
------------------------------------------------------------
"""

import logging
import asyncio
from datetime import datetime

from trend_system_final import analyze_and_format
from notifier import send_message
from database import get_signals, update_operation_status

logger = logging.getLogger("signal_reactivation_sync")

# ================================================================
# 👁 Estado del módulo de reactivación (usado por /estado)
# ================================================================
reactivation_status = {
    "running": False,
    "last_run": None,
    "monitored_signals": 0,
}


def get_reactivation_status():
    """Devuelve el estado actual del módulo de reactivación."""
    return reactivation_status


# ================================================================
# ♻️ Reactivación individual de una señal
# ================================================================
def check_reactivation(symbol: str, direction: str, leverage: int = 20, entry: float = None):
    """
    Analiza nuevamente una señal descartada o en espera.
    Si la alineación técnica es ≥ 75 % y el mensaje la considera
    válida para entrada, se marca como reactivada y se envía
    una notificación automática por Telegram.
    """
    try:
        logger.info(f"♻️ Revisando reactivación para {symbol} ({direction.upper()})...")

        # --- Ejecutar análisis técnico completo ---
        result, report = analyze_and_format(symbol, direction_hint=direction)
        match_ratio = result.get("match_ratio", 0)
        recommendation = result.get("recommendation", "Desconocida")

        # --- Evaluar condiciones para reactivación ---
        text = recommendation.lower()
        cond_ok = (
            match_ratio >= 75
            and (
                "confirmada" in text
                or "oportunidades" in text
                or "entrada" in text
            )
        )

        if cond_ok:
            logger.info(f"✅ Señal {symbol} cumple criterios para reactivación ({match_ratio:.1f}%)")

            update_operation_status(symbol, "reactivada", match_ratio)
            msg = (
                f"♻️ *Reactivación detectada: {symbol}*\n\n"
                f"📊 Dirección: *{direction.upper()}*\n"
                f"⚙️ Match técnico: *{match_ratio:.1f}%*\n"
                f"💬 Estado: *Reactivada antes del Entry original*\n\n"
                f"{report}"
            )
            send_message(msg)
            return {"symbol": symbol, "match": match_ratio, "status": "reactivada"}

        else:
            logger.info(f"⏳ {symbol}: sin condiciones suficientes ({match_ratio:.1f}%, {recommendation})")
            return {"symbol": symbol, "match": match_ratio, "status": "sin cambios"}

    except Exception as e:
        logger.error(f"❌ Error verificando reactivación de {symbol}: {e}")
        return None


# ================================================================
# 🔁 Bucle automático de reactivación
# ================================================================
async def auto_reactivation_loop(interval: int = 900):
    """
    Evalúa periódicamente las señales marcadas como 'en espera' o 'descartadas'.
    Ideal para ejecutarse en un task paralelo (lo hace main.py).
    """
    logger.info("🔁 Iniciando monitoreo automático de reactivaciones...")

    while True:
        reactivation_status["running"] = True
        reactivation_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            signals = get_signals(limit=50)
            reactivation_status["monitored_signals"] = len(signals)

            if not signals:
                logger.info("📭 No hay señales en base de datos para revisar.")
                await asyncio.sleep(interval)
                continue

            for sig in signals:
                recommendation = (sig.get("recommendation") or "").upper()
                # Solo revisamos las que quedaron como "ESPERAR" o "DESCARTAR"
                if "ESPERAR" in recommendation or "DESCARTAR" in recommendation:
                    symbol = sig.get("pair")
                    direction = sig.get("direction", "long")
                    leverage = sig.get("leverage", 20)
                    entry = sig.get("entry", None)
                    check_reactivation(symbol, direction, leverage, entry)

            logger.info(f"🕒 Ciclo completado. Próxima revisión en {interval//60} minutos.")
            await asyncio.sleep(interval)

        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación automática: {e}")
            await asyncio.sleep(60)


# ================================================================
# 🚀 Ejecución directa (modo independiente)
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    try:
        asyncio.run(auto_reactivation_loop())
    except KeyboardInterrupt:
        print("\n🛑 Reactivación detenida manualmente.")
