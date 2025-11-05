import logging
import time
from datetime import datetime
from indicators import get_indicators
from divergence_detector import detect_divergences
from trend_analysis import analyze_trend
from notifier import notify_reactivation
from database import update_operation_status, get_signals
from helpers import calculate_match_ratio

logger = logging.getLogger("signal_reactivation")

# ================================================================
# ♻️ Módulo de Reactivación de Señales
# ================================================================
def check_reactivation(symbol: str, direction: str, leverage: int = 20, entry: float = None):
    """
    Reanaliza señales descartadas o en espera.
    Si la estructura técnica mejora antes de alcanzar el Entry original,
    puede marcar la señal como 'reactivada' y notificar al usuario.
    """
    try:
        logger.info(f"♻️ Revisando posible reactivación para {symbol} ({direction.upper()})")

        # === 1️⃣ Obtener indicadores en 3 temporalidades ===
        tf_list = ["1m", "5m", "15m"]
        data = get_indicators(symbol, tf_list)

        if not data or len(data) < 3:
            logger.warning(f"⚠️ Datos insuficientes para {symbol} en {tf_list}")
            return None

        # === 2️⃣ Analizar divergencias RSI/MACD ===
        divergences = detect_divergences(symbol, data)
        strong_divs = [d for d in divergences if d["strength"] in ("strong", "moderate")]

        # === 3️⃣ Confirmar dirección del mercado ===
        trend_info = analyze_trend(symbol, data)
        match_ratio = calculate_match_ratio(trend_info, direction)

        # === 4️⃣ Evaluar condiciones de reactivación ===
        if match_ratio >= 0.75 and len(strong_divs) <= 1:
            # Señal coherente, condiciones estables
            logger.info(f"✅ Señal {symbol} cumple criterios para reactivación ({match_ratio*100:.1f}%)")

            # === 5️⃣ Actualizar base de datos y notificar ===
            update_operation_status(symbol, "reactivada", match_ratio * 100)

            msg = (
                f"♻️ *{symbol}* ha mostrado alineación técnica favorable antes del Entry original.\n\n"
                f"📊 Dirección: *{direction.upper()}*\n"
                f"⚙️ Match técnico: *{match_ratio*100:.1f}%*\n"
                f"💬 Divergencias detectadas: {len(divergences)}\n\n"
                f"✅ *Reactivación confirmada - Entrada anticipada sugerida.*"
            )
            notify_reactivation(symbol, msg)
            return {"symbol": symbol, "match": match_ratio, "status": "reactivada"}

        else:
            logger.info(
                f"⏳ {symbol}: sin condiciones suficientes para reactivación "
                f"(Match={match_ratio*100:.1f}%, Div={len(divergences)})"
            )
            return {"symbol": symbol, "match": match_ratio, "status": "sin cambios"}

    except Exception as e:
        logger.error(f"❌ Error en reactivación de {symbol}: {e}")
        return None


# ================================================================
# 🔄 Revisión periódica automática
# ================================================================
def auto_reactivation_loop(interval: int = 900):
    """
    Evalúa periódicamente las señales marcadas como 'en espera' o 'descartadas'.
    Ideal para ejecución en hilo paralelo o programador de tareas.
    """
    logger.info("🔁 Iniciando monitoreo automático de reactivaciones...")
    while True:
        try:
            signals = get_signals(limit=20)
            for sig in signals:
                if sig["recommendation"] in ["ESPERAR MEJOR ENTRADA", "DESCARTAR"]:
                    check_reactivation(
                        sig["pair"],
                        sig["direction"],
                        sig["leverage"],
                        sig["entry"]
                    )
            logger.info("🕒 Ciclo completado. Próxima revisión en 15 minutos.")
            time.sleep(interval)
        except Exception as e:
            logger.error(f"❌ Error en ciclo de reactivación: {e}")
            time.sleep(60)
