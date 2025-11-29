"""
controllers/signal_controller.py
--------------------------------
Procesa una señal nueva desde Telegram:
  ✔ parseo
  ✔ guardado en DB
  ✔ análisis técnico con motor unificado
  ✔ notificación por Telegram
"""

import logging

from core.signal_engine import analyze_signal
from services import db_service
from services.telegram_service import send_message

from models.signal import Signal
from utils.helpers import parse_signal_text
from utils.formatters import (
    format_signal_intro,
    format_analysis_result
)

logger = logging.getLogger("signal_controller")


async def process_new_signal(text: str):
    """
    Pasos:
      1) parsear texto
      2) insertar señal en DB
      3) ejecutar motor técnico
      4) enviar resultado
    """
    try:
        parsed = parse_signal_text(text)
        if not parsed:
            logger.warning("⚠️ Mensaje recibido pero no es una señal válida.")
            return

        logger.info(f"🔍 Nueva señal detectada: {parsed['symbol']}")

        # Guardar en DB
        signal_id = db_service.create_signal(parsed)
        if not signal_id:
            logger.error("❌ No se logró insertar señal en DB.")
            return

        signal = Signal(
            id=signal_id,
            symbol=parsed["symbol"],
            direction=parsed["direction"],
            entry=parsed["entry"],
            tp_list=parsed["tp_list"],
            sl=parsed["sl"]
        )

        # Análisis técnico
        analysis = analyze_signal(signal)

        # Enviar a Telegram
        msg = (
            format_signal_intro(signal)
            + "\n"
            + format_analysis_result(analysis)
        )

        await send_message(msg)

        # Registrar match_ratio
        db_service.set_signal_match_ratio(signal_id, analysis.get("match_ratio", 0))

    except Exception as e:
        logger.error(f"❌ Error en process_new_signal: {e}")
