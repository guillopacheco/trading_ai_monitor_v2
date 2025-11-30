"""
controllers/signal_controller.py
--------------------------------
Controlador encargado del procesamiento de señales nuevas recibidas.

Flujo:
    telegram_service / telegram_router
        → signal_listener.on_new_signal(event)
        → process_new_signal(raw_text)
        → core.signal_engine.analyze_signal
        → db_service (opcional)
        → telegram_service.send_message
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

# Importamos helpers; si no existen, usamos un fallback simple.
try:
    from utils.helpers import parse_signal_text, now_ts
except Exception:  # pragma: no cover - fallback
    from datetime import datetime

    def now_ts() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    def parse_signal_text(text: str) -> Dict[str, Any]:
        """
        Fallback MUY simple: intenta extraer solo el símbolo y la dirección.
        Se recomienda implementar parse_signal_text real en utils/helpers.py.
        """
        t = text.upper()
        direction = "long"
        if "SHORT" in t or "SELL" in t:
            direction = "short"
        # símbolo: primera palabra tipo XXXUSDT
        symbol = "UNKNOWN"
        for token in t.replace("#", " ").split():
            if token.endswith("USDT"):
                symbol = token
                break
        return {
            "raw_text": text,
            "symbol": symbol,
            "direction": direction,
        }

# Motor técnico A+
try:
    from core.signal_engine import analyze_signal
except Exception:
    # En algunos entornos el módulo puede estar en la raíz
    from signal_engine import analyze_signal  # type: ignore

# db_service como módulo completo para poder usar hasattr()
try:
    import services.db_service as db_service  # type: ignore
except Exception:  # pragma: no cover
    db_service = None  # type: ignore


logger = logging.getLogger("signal_controller")


# ============================================================
# 🔹 FUNCIÓN PRINCIPAL: procesar nueva señal
# ============================================================

async def process_new_signal(raw_text: str) -> Dict[str, Any]:
    """
    Procesa una señal nueva proveniente del canal VIP.

    Pasos:
        1) Parsear texto crudo.
        2) Guardar señal en DB (si db_service lo soporta).
        3) Ejecutar análisis técnico con el Motor A+.
        4) Registrar log de análisis en DB (si aplica).
        5) Enviar resultado a Telegram.
    """
    logger.info("📩 Iniciando procesamiento de nueva señal...")

    # 1) Parsear texto crudo
    try:
        parsed = parse_signal_text(raw_text)
        logger.debug(f"🧾 Señal parseada: {parsed}")
    except Exception as e:
        logger.error(f"❌ Error parseando señal: {e}")
        parsed = {
            "raw_text": raw_text,
            "symbol": "UNKNOWN",
            "direction": "long",
        }

    symbol = parsed.get("symbol", "UNKNOWN")
    direction = parsed.get("direction", "long")

    # 2) Guardar señal en DB (solo si el servicio lo soporta)
    signal_id: Optional[int] = None
    if db_service is not None:
        try:
            payload = {
                "symbol": symbol,
                "direction": direction,
                "raw_text": raw_text,
                "created_at": now_ts(),
            }
            if hasattr(db_service, "create_signal"):
                signal_id = db_service.create_signal(payload)  # type: ignore
                logger.info(f"🗄 Señal registrada en DB con id={signal_id}")
        except Exception as e:
            logger.error(f"⚠️ No se pudo guardar la señal en DB: {e}")

    # 3) Ejecutar análisis técnico con el Motor A+
    try:
        analysis = await analyze_signal(symbol, direction)
    except Exception as e:
        logger.exception(f"❌ Error ejecutando analyze_signal: {e}")
        analysis = {
            "ok": False,
            "error": str(e),
            "text": f"⚠️ Error analizando la señal de {symbol}.",
            "entry_grade": "D",
            "global_score": 0.0,
        }

    # 4) Registrar log de análisis en DB (si hay función disponible)
    if db_service is not None and signal_id is not None:
        try:
            if hasattr(db_service, "add_analysis_log"):
                db_service.add_analysis_log(  # type: ignore
                    signal_id=signal_id,
                    timestamp=now_ts(),
                    result=analysis,
                )
                logger.info(f"🗄 Log de análisis registrado para señal {signal_id}.")
        except Exception as e:
            logger.error(f"⚠️ No se pudo registrar el log de análisis: {e}")

    # 5) Enviar resultado a Telegram
    try:
        # Import local para evitar ciclos: telegram_service → signal_listener → signal_controller
        from services.telegram_service import send_message  # type: ignore

        text = analysis.get("text") or "⚠️ Análisis sin mensaje formateado."
        await send_message(text)
        logger.info(f"📨 Resultado enviado a Telegram para {symbol}.")
    except Exception as e:
        logger.error(f"❌ Error enviando resultado a Telegram: {e}")

    return analysis
