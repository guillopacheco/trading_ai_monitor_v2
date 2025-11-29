"""
controllers/signal_controller.py
--------------------------------
Controlador encargado del procesamiento de señales nuevas recibidas.

Flujo:
    telegram_router → process_new_signal → db_service + signal_engine + telegram_service
"""

from __future__ import annotations
import logging

from services.db_service import (
    save_new_signal,
    save_analysis_log,
)

from core.signal_engine import (
    analyze_signal,
)

from services.telegram_service import safe_send

from utils.helpers import now_ts

logger = logging.getLogger("signal_controller")


# ==================================================================
# 🟦 Procesamiento de señal nueva
# ==================================================================

def process_new_signal(signal_obj):
    """
    Procesa una señal recién llegada del canal VIP.

    Pasos:
        1. Guardar señal cruda en DB
        2. Ejecutar motor técnico
        3. Guardar análisis en DB
        4. Enviar respuesta a Telegram
    """

    logger.info(f"📩 Procesando nueva señal: {signal_obj.symbol}")

    # 1️⃣ Guardar la señal original en DB
    signal_id = save_new_signal(signal_obj)
    logger.info(f"🗄 Señal guardada con ID {signal_id}")

    # 2️⃣ Correr motor técnico A+
    analysis = analyze_signal(signal_obj)

    # 3️⃣ Guardar análisis (para historial completo)
    save_analysis_log(
        signal_id=signal_id,
        timestamp=now_ts(),
        result=analysis.get("raw", {}),
        allowed=analysis.get("allowed", False),
        reason=analysis.get("reason", "Sin motivo"),
    )

    # 4️⃣ Enviar mensaje a Telegram
    try:
        safe_send(analysis["message"])
    except Exception as e:
        logger.error(f"❌ Error enviando resultado a Telegram: {e}")

    return analysis
