import asyncio
import logging
import time
from datetime import datetime

from helpers import get_current_price, calculate_roi
from indicators import get_technical_data
from trend_analysis import analyze_trend
from notifier import notify_operation_alert  # ✅ nombre corregido
from database import update_operation_status, get_alert_record, update_alert_record
from config import (
    SIMULATION_MODE,
    ROI_REVERSION_THRESHOLD,
    ROI_DYNAMIC_STOP_THRESHOLD,
    ROI_TAKE_PROFIT_THRESHOLD
)

logger = logging.getLogger("operation_tracker")


# ================================================================
# ⚙️ Función principal de monitoreo
# ================================================================
async def monitor_open_positions(positions):
    """
    Monitorea las operaciones abiertas periódicamente.
    Si el ROI cae por debajo de los umbrales definidos, ejecuta análisis técnico.
    """
    if not positions:
        logger.info("ℹ️ No hay posiciones abiertas para monitorear.")
        return

    logger.info(f"🧭 Iniciando monitoreo de {len(positions)} operaciones abiertas...")

    while positions:
        for pos in positions:
            symbol = pos["symbol"]
            direction = pos["direction"].lower()
            entry = float(pos["entry"])
            leverage = int(pos["leverage"])

            try:
                # =========================================================
                # 🔹 Obtener precio actual (simulado o real)
                # =========================================================
                current_price = get_current_price(symbol)
                if current_price is None:
                    logger.warning(f"⚠️ No se pudo obtener precio para {symbol}.")
                    continue

                roi = calculate_roi(entry, current_price, direction, leverage)
                vol_label = "HIGH" if abs(roi) > ROI_DYNAMIC_STOP_THRESHOLD else "LOW"

                logger.info(f"⏱️ {symbol}: ROI {roi:.2f}% | Vol {vol_label}")

                # =========================================================
                # ⚠️ Verificar umbrales de pérdida o ganancia
                # =========================================================
                alert_level = None
                if roi <= ROI_REVERSION_THRESHOLD:
                    alert_level = "LOSS"
                elif roi >= ROI_TAKE_PROFIT_THRESHOLD:
                    alert_level = "TP"
                elif roi >= ROI_DYNAMIC_STOP_THRESHOLD:
                    alert_level = "WARNING"

                if alert_level:
                    # Registrar o verificar alerta previa
                    existing_alert = get_alert_record(symbol)
                    if not existing_alert or existing_alert["level"] != alert_level:
                        await handle_operation_alert(
                            symbol=symbol,
                            direction=direction,
                            entry=entry,
                            leverage=leverage,
                            roi=roi,
                            vol_label=vol_label,
                            alert_level=alert_level,
                        )
                        update_alert_record(symbol, alert_level)
                    else:
                        logger.debug(f"🔁 Alerta ya registrada para {symbol} ({alert_level})")

                # =========================================================
                # 💾 Actualizar en la base de datos
                # =========================================================
                update_operation_status(symbol, "open", roi)

                # =========================================================
                # 💤 Pausa adaptativa según ROI y volatilidad
                # =========================================================
                sleep_time = 300 if abs(roi) < 20 else 120  # 5min normal, 2min en alerta
                logger.info(f"⏳ Próximo chequeo en {sleep_time / 60:.1f} min ({symbol})...")
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"❌ Error monitoreando {symbol}: {e}")

        await asyncio.sleep(5)


# ================================================================
# 🚨 Evaluación técnica cuando hay alerta de pérdida o ganancia
# ================================================================
async def handle_operation_alert(symbol, direction, entry, leverage, roi, vol_label, alert_level):
    """
    Ejecuta un análisis técnico multi-temporal para decidir si cerrar,
    mantener o revertir una posición en alerta.
    """
    try:
        logger.warning(f"🚨 Alerta detectada en {symbol} ({alert_level}) ROI {roi:.2f}%")

        # =========================================================
        # 🧠 Obtener indicadores multi-TF
        # =========================================================
        data_by_tf = get_technical_data(symbol)
        if not data_by_tf:
            msg = f"⚠️ Datos insuficientes para ATR de {symbol}"
            logger.warning(msg)
            notify_operation_alert(symbol, direction, roi, vol_label, msg)
            return

        # =========================================================
        # 📊 Analizar tendencia técnica
        # =========================================================
        analysis = analyze_trend(symbol, direction, entry, data_by_tf, leverage)
        recommendation = analysis.get("recommendation", "EVALUAR")
        match_ratio = analysis.get("match_ratio", 0)

        # =========================================================
        # 💬 Enviar alerta con recomendación técnica
        # =========================================================
        message = (
            f"⚠️ *ALERTA DE OPERACIÓN*\n\n"
            f"🪙 *Par:* {symbol}\n"
            f"📈 *Dirección:* {direction.upper()}\n"
            f"💰 *ROI actual:* {roi:.2f}%\n"
            f"🌡️ *Volatilidad:* {vol_label}\n"
            f"📊 *Match Ratio:* {match_ratio:.2f}\n\n"
            f"📌 *Recomendación técnica:* {recommendation}"
        )

        notify_operation_alert(symbol, direction, roi, vol_label, message)
        logger.warning(f"🚨 Alerta enviada: {symbol} {alert_level} ({roi:.2f}%)")

    except Exception as e:
        logger.error(f"❌ Error durante análisis técnico de alerta {symbol}: {e}")


# ================================================================
# 🧪 Ejecutar monitoreo en modo de prueba
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_positions = [
        {"symbol": "BTCUSDT", "direction": "long", "entry": 71000, "leverage": 20},
        {"symbol": "ETHUSDT", "direction": "short", "entry": 3600, "leverage": 20},
    ]
    asyncio.run(monitor_open_positions(test_positions))
