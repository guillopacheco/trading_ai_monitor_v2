# ================================================================
# signal_service.py — VERSIÓN FINAL 2025-12
# Servicio oficial y único para gestionar señales
# ================================================================
import json
import logging
from database import (
    save_signal,
    get_pending_signals_for_reactivation,
    mark_signal_reactivated,
    save_analysis_log
)

logger = logging.getLogger("signal_service")


class SignalService:
    """
    Servicio centralizado de señales.
    Usado por:
    • telegram_reader → para registrar señales entrantes
    • signal_coordinator → para procesarlas
    • signal_reactivation_sync → para reactivar señales pendientes
    """

    # ------------------------------------------------------------
    # 1) REGISTRAR SEÑAL NUEVA (vía Telegram)
    # ------------------------------------------------------------
    def register_signal(self, symbol: str, direction: str, raw_text: str) -> int:
        """
        Registra la señal en la base de datos.
        Devuelve el signal_id generado.
        """

        payload = {
            "symbol": symbol.upper(),
            "direction": direction.lower(),
            "raw_text": raw_text
        }

        try:
            signal_id = save_signal(payload)
            logger.info(f"📥 Señal registrada | ID={signal_id} | {symbol} {direction}")
            return signal_id

        except Exception as e:
            logger.error(f"❌ Error al registrar la señal: {e}")
            return None

    # ------------------------------------------------------------
    # 2) OBTENER SEÑALES PENDIENTES DE REACTIVACIÓN
    # ------------------------------------------------------------
    def get_pending_signals(self):
        """
        Devuelve una lista de todas las señales en estado 'pending'.
        Usado por signal_reactivation_sync.
        """
        try:
            pending = get_pending_signals_for_reactivation()
            logger.info(f"🔎 {len(pending)} señal(es) pendiente(s) para reactivación.")
            return pending

        except Exception as e:
            logger.error(f"❌ Error obteniendo señales pendientes: {e}")
            return []

    # ------------------------------------------------------------
    # 3) GUARDAR LOG DE ANÁLISIS (entrada/reactivación)
    # ------------------------------------------------------------
    def save_analysis_log(self, signal_id, context, analysis):
        try:
            if isinstance(analysis, dict):
                analysis = json.dumps(analysis, ensure_ascii=False)

            save_analysis_log(signal_id, context, analysis)

        except Exception as e:
            logger.error(f"❌ Error guardando log de análisis (ID={signal_id}): {e}")

    # ------------------------------------------------------------
    # 4) MARCAR UNA SEÑAL COMO REACTIVADA
    # ------------------------------------------------------------
    def mark_reactivated(self, signal_id: int):
        """
        Cambia el estado de la señal a 'reactivated'
        """
        try:
            mark_signal_reactivated(signal_id)
            logger.info(f"⚡ Señal reactivada | ID={signal_id}")

        except Exception as e:
            logger.error(f"❌ Error marcando señal reactivada (ID={signal_id}): {e}")
