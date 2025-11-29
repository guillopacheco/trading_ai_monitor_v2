"""
controllers/signal_controller.py
--------------------------------
Capa intermedia entre:

    telegram_router.py  → señales entrantes (texto)
    signal_engine.py    → análisis técnico
    db_service.py       → guardado y estados
    telegram_service.py → notificaciones

Este controlador NO accede directamente a Telegram ni a Bybit.
Solo coordina.
"""

import logging
from typing import Optional, Dict

from core.signal_engine import (
    parse_raw_signal,
    analyze_signal,
)
from services import db_service
from utils.formatters import (
    format_signal_intro,
    format_analysis_summary,
)
from services.telegram_service import send_message

logger = logging.getLogger("signal_controller")


# ============================================================
# 🔥 PROCESAR SEÑALES NUEVAS
# ============================================================

def process_new_signal(raw_text: str):
    """
    Recibe el texto del canal VIP → lo parsea → analiza → guarda → notifica.
    """

    logger.info("📩 Nueva señal recibida desde Telegram.")

    # 1. Parsear texto
    sig = parse_raw_signal(raw_text)
    if sig is None:
        logger.warning("❗ Señal ignorada: no se pudo parsear.")
        return

    # 2. Guardar en DB como pending
    signal_id = db_service.create_signal(
        symbol=sig.symbol,
        direction=sig.direction,
        raw_text=sig.raw_text,
        status="pending",
    )

    logger.info(f"🗄 Guardada señal {sig.symbol} (id={signal_id}) como pending.")

    # 3. Ejecutar análisis técnico
    result = analyze_signal(sig)

    # 4. Preparar mensaje formateado
    header = format_signal_intro(signal.symbol, signal.direction)
    detail = format_full_analysis(result["analysis"])
    final_msg = f"{header}\n{detail}"

    # 5. Enviar mensaje al usuario
    send_message(final_msg)

    # 6. Actualizar DB con resultado
    db_service.save_analysis(
        signal_id=signal_id,
        match_ratio=result["analysis"]["match_ratio"],
        technical_score=result["analysis"]["technical_score"],
        grade=result["analysis"]["grade"],
        decision=result["analysis"]["decision"],
    )

    logger.info(f"✔ Señal procesada y análisis guardado (id={signal_id}).")
