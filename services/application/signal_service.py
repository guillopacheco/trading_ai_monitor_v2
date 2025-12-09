# ================================================================
# signal_service.py — versión corregida y compatible con coordinadores
# ================================================================

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
    Servicio oficial para:
    • Registrar señales nuevas
    • Consultar pendientes de reactivación
    • Registrar logs de análisis (entrada y reactivación)
    """

    # ------------------------------------------------------------
    # 1. REGISTRAR SEÑAL (usado por telegram_reader)
    # ------------------------------------------------------------
    def register_signal(self, symbol: str, direction: str, raw_text: str) -> int:
        """
        Registrar señal en la DB. Devuelve el ID.
        El coordinator NO debe construir la estructura completa.
        """

        signal_data = {
            "symbol": symbol.upper(),
            "direction": direction.lower(),
            "raw_text": raw_text
        }

        try:
            signal_id = save_signal(signal_data)
            logger.info(f"📥 Señal registrada en DB → {signal_id} | {symbol} {direction}")
            return signal_id

        except Exception as e:
            logger.error(f"❌ Error registrando señal: {e}")
            return None

    # ------------------------------------------------------------
    # 2. OBTENER SEÑALES PENDIENTES PARA REACTIVACIÓN
    # ------------------------------------------------------------
    def get_pending_signals(self):
        try:
            results = get_pending_signals_for_reactivation()
            logger.info(f"🔎 {len(results)} señales pendientes para reactivación.")
            return results
        except Exception as e:
            logger.error(f"❌ Error cargando pendientes: {e}")
            return []

    # ------------------------------------------------------------
    # 3. GUARDAR LOG DE ANÁLISIS (entrada o reactivación)
    # ------------------------------------------------------------
    def save_analysis_log(self, signal_id: int, analysis: dict, context: str):
        try:
            save_analysis_log(
                signal_id=signal_id,
                context=context,
                analysis_json=analysis
            )
            logger.info(f"📝 Log técnico guardado ({context}) para ID {signal_id}")
        except Exception as e:
            logger.error(f"❌ Error guardando log técnico: {e}")

    # ------------------------------------------------------------
    # 4. MARCAR SEÑAL COMO REACTIVADA
    # ------------------------------------------------------------
    def mark_reactivated(self, signal_id: int):
        try:
            mark_signal_reactivated(signal_id)
            logger.info(f"⚡ Señal marcada como reactivada → ID {signal_id}")
        except Exception as e:
            logger.error(f"❌ Error marcando señal reactivada: {e}")
