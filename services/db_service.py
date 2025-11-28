"""
db_service.py
-------------
Capa de servicio que abstrae por completo el acceso a la base de datos SQLite.

Objetivos:
- Ser la única interfaz oficial para leer/escribir señales, posiciones y logs.
- Reemplazar gradualmente el uso directo de `database.py` y `signal_manager_db.py`.
- Proveer una API limpia, estable y fácil de usar.
- Mantener compatibilidad con la base de datos existente.
"""

import logging
from typing import List, Dict, Optional, Any

from signal_manager_db import (
    save_new_signal,
    get_signal_by_id,
    get_pending_signals_for_reactivation,
    update_signal_match_ratio,
    mark_signal_reactivated,
    mark_signal_as_ignored,
    save_analysis_log,
    get_recent_logs,
)

from database import (
    init_db,
    execute_query,
    fetch_query,
)

logger = logging.getLogger("db_service")


# ================================================================
# 🔵 Inicialización (se llama desde main)
# ================================================================
def initialize():
    """
    Inicializa la base de datos usando el módulo existente.
    """
    try:
        init_db()
        logger.info("🗄 Base de datos conectada correctamente (db_service).")
    except Exception as e:
        logger.error(f"❌ Error inicializando DB: {e}")


# ================================================================
# 🔵 Sección: Señales
# ================================================================
def create_signal(signal_data: Dict[str, Any]) -> Optional[int]:
    """
    Guarda una nueva señal en la base de datos.
    Retorna el ID de la nueva señal.
    """
    try:
        signal_id = save_new_signal(signal_data)
        logger.info(f"🟢 Señal registrada en DB (id={signal_id}).")
        return signal_id
    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")
        return None


def get_signal(id_signal: int) -> Optional[Dict[str, Any]]:
    """
    Recupera una señal por ID.
    """
    try:
        return get_signal_by_id(id_signal)
    except Exception as e:
        logger.error(f"❌ Error leyendo señal {id_signal}: {e}")
        return None


def get_pending_reactivation_signals() -> List[Dict[str, Any]]:
    """
    Lista todas las señales pendientes de reactivación.
    """
    try:
        return get_pending_signals_for_reactivation()
    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes: {e}")
        return []


def set_signal_match_ratio(signal_id: int, ratio: float):
    """
    Actualiza el match_ratio de una señal.
    """
    try:
        update_signal_match_ratio(signal_id, ratio)
    except Exception as e:
        logger.error(f"⚠️ Error actualizando match_ratio de señal {signal_id}: {e}")


def set_signal_reactivated(signal_id: int):
    """
    Cambia estado de una señal a 'reactivada'.
    """
    try:
        mark_signal_reactivated(signal_id)
        logger.info(f"♻️ Señal {signal_id} marcada como reactivada.")
    except Exception as e:
        logger.error(f"⚠️ Error marcando señal como reactivada: {e}")


def set_signal_ignored(signal_id: int):
    """
    Marca la señal como ignorada (por análisis técnico negativo).
    """
    try:
        mark_signal_as_ignored(signal_id)
        logger.info(f"🚫 Señal {signal_id} marcada como ignorada.")
    except Exception as e:
        logger.error(f"⚠️ Error marcando señal como ignorada: {e}")


# ================================================================
# 🔵 Sección: Logs técnicos
# ================================================================
def add_analysis_log(signal_id: int, match_ratio: float, recommendation: str, details: Any):
    """
    Guarda un registro del análisis técnico generado por el motor.
    """
    try:
        save_analysis_log(
            signal_id=signal_id,
            match_ratio=match_ratio,
            recommendation=recommendation,
            details=details,
        )
    except Exception as e:
        logger.error(f"⚠️ Error guardando análisis técnico ({signal_id}): {e}")


def get_logs(limit: int = 50) -> List[Dict]:
    """
    Recupera los logs más recientes del sistema.
    """
    try:
        return get_recent_logs(limit)
    except Exception as e:
        logger.error(f"❌ Error obteniendo logs recientes: {e}")
        return []


# ================================================================
# 🔵 Sección: utilidades SQL directas
# (para uso interno, no recomendado a los demás módulos)
# ================================================================
def raw_query(sql: str, params: tuple = ()) -> List[Dict]:
    """
    Ejecuta una consulta SELECT cruda.
    """
    try:
        return fetch_query(sql, params)
    except Exception as e:
        logger.error(f"❌ Error ejecutando query SQL: {e}")
        return []


def raw_execute(sql: str, params: tuple = ()) -> bool:
    """
    Ejecuta un UPDATE/INSERT/DELETE crudo.
    """
    try:
        execute_query(sql, params)
        return True
    except Exception as e:
        logger.error(f"❌ Error ejecutando SQL: {e}")
        return False


# ================================================================
# 🔵 Prueba directa
# ================================================================
if __name__ == "__main__":
    initialize()
    print(get_logs(5))
