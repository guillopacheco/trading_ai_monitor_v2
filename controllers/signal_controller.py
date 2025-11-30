"""
controllers/signal_controller.py
--------------------------------
Controlador del flujo de una señal nueva recibida desde el canal VIP.

Flujo:
    telegram_router → process_new_signal → db_service + signal_engine + telegram_service
"""

import logging
from services.db_service import save_new_signal, add_analysis_log
from core.signal_engine import analyze_signal_text
from services.telegram_service import safe_send
from utils.helpers import now_ts

logger = logging.getLogger("signal_controller")


async def process_new_signal(raw_text: str) -> None:
    """
    Procesa una señal textualmente tal como llega del canal VIP.
    """
    text = (raw_text or "").strip()
    if not text:
        logger.warning("⚠️ process_new_signal llamado con texto vacío.")
        return

    logger.info("📥 Registrando nueva señal en DB...")
    # 1️⃣ Guardar señal cruda (devuelve ID)
    signal_id = save_new_signal(text)

    logger.info(f"🧠 Analizando señal ID={signal_id}...")
    # 2️⃣ Ejecutar motor técnico unificado
    analysis = analyze_signal_text(text)

    # 3️⃣ Guardar log de análisis
    add_analysis_log(
        signal_id=signal_id,
        timestamp=now_ts(),
        result=analysis.get("raw", {}),
        allowed=analysis.get("allowed", False),
        reason=analysis.get("reason", "Sin motivo"),
    )

    # 4️⃣ Enviar mensaje formateado a Telegram
    msg = analysis.get("message", "📊 Análisis completado (sin mensaje formateado).")
    try:
        await safe_send(msg)
    except Exception as e:
        logger.error(f"❌ Error enviando resultado a Telegram: {e}")
