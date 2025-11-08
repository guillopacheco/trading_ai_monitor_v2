# operation_tracker.py
import logging
import time
from bybit_client import get_open_positions
from indicators import get_technical_data
from trend_analysis import analyze_trend
from notifier import notify_operation_alert

logger = logging.getLogger("operation_tracker")

LOSS_STEPS = [-30, -50, -70, -90]  # ejemplo de niveles de pérdida (por ROI %)
CHECK_BASE_SECONDS = 60           # ciclo base de evaluación (1 min)

def _classify_volatility(indicators_by_tf):
    # Simple: usa ATR_rel promedio si está disponible
    vals = []
    for tf, d in indicators_by_tf.items():
        v = d.get("atr_rel")
        if v is not None:
            vals.append(v)
    if not vals:
        return "LOW"
    avg = sum(vals) / len(vals)
    if avg > 0.03:
        return "HIGH"
    if avg > 0.015:
        return "MEDIUM"
    return "LOW"

def _suggestion_from_result(result):
    rec = (result or {}).get("recommendation", "ESPERAR")
    if rec in ("ENTRADA", "ENTRADA_CON_PRECAUCION"):
        return "Mantener (tendencia a favor)"
    if rec == "ESPERAR":
        return "Evaluar / reducir riesgo"
    return "Cerrar o revertir"

def monitor_open_positions(initial_positions=None):
    """
    Monitorea posiciones reales en Bybit.
    - Si initial_positions es None, las consulta cada ciclo.
    - Calcula análisis técnico por posición y dispara alertas cuando corresponde.
    """
    logger.info("🧭 Iniciando monitoreo de operaciones abiertas...")

    while True:
        try:
            positions = initial_positions or get_open_positions()
            if not positions:
                logger.info("ℹ️ No hay posiciones activas. Reintentando más tarde...")
                time.sleep(30)
                continue

            for pos in positions:
                symbol = pos.get("symbol", "").upper()
                direction = pos.get("direction", "").lower()
                entry = float(pos.get("entry", 0))
                lev = int(pos.get("leverage", 20))

                # Indicadores
                indicators = get_technical_data(symbol, intervals=["1m", "5m", "15m"])
                if not indicators:
                    logger.warning(f"⚠️ Datos insuficientes para {symbol}")
                    continue

                # (Aquí podrías calcular ROI real desde tu exchange; placeholder -999 indica que debes integrarlo)
                roi = float(pos.get("roi", -999.0))  # integra tu ROI real si lo tienes

                result = analyze_trend(symbol, direction, entry, indicators, lev)
                vol = _classify_volatility(indicators)
                suggestion = _suggestion_from_result(result)

                # Gatillos por pérdidas (si tienes ROI real, cámbialo aquí)
                for step in LOSS_STEPS:
                    if roi <= step:
                        notify_operation_alert(symbol, direction, roi, step, vol, suggestion)
                        break

                # Ritmo según volatilidad
                if vol == "HIGH":
                    sleep_s = max(300, CHECK_BASE_SECONDS * 0.5)
                elif vol == "MEDIUM":
                    sleep_s = CHECK_BASE_SECONDS
                else:
                    sleep_s = CHECK_BASE_SECONDS * 1.2

                logger.info(f"⏱️ {symbol}: ROI {roi:.2f}% | Vol {vol} | Próximo check en {sleep_s/60:.1f} min")

            # Si las posiciones se pasan “initial_positions”, solo 1 ciclo
            if initial_positions is not None:
                return

            time.sleep(15)

        except Exception as e:
            logger.error(f"❌ Error en monitor_open_positions: {e}")
            time.sleep(20)
