"""
signal_manager_db.py — Módulo oficial para gestionar señales en SQLite
-----------------------------------------------------------------------

Este módulo reemplaza completamente al antiguo.
Compatible con:
- telegram_reader.py (save_signal)
- signal_reactivation_sync.py
- database.py

Columnas usadas en tabla `signals`:
    id INTEGER PRIMARY KEY
    symbol TEXT
    direction TEXT
    leverage INTEGER
    entry_price REAL
    take_profits TEXT (csv)
    match_ratio REAL
    status TEXT ('pending', 'reactivated', 'ignored')
    created_at TEXT
    reactivated_at TEXT

Funciones incluidas:
✔ get_pending_signals_for_reactivation()
✔ mark_signal_reactivated()
✔ update_signal_match_ratio()
✔ save_analysis_log()
"""

import sqlite3
import logging
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger("signal_manager_db")


# ------------------------------------------------------------
# 📌 Conexión segura
# ------------------------------------------------------------
def _get_conn():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


# ------------------------------------------------------------
# 📌 Obtener señales pendientes
# ------------------------------------------------------------
def get_pending_signals_for_reactivation():
    """
    Devuelve una lista de señales con:
    status = 'pending'
    entry_price != NULL
    """

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage, entry_price,
                   take_profits, created_at
            FROM signals
            WHERE status = 'pending'
              AND entry_price IS NOT NULL
            ORDER BY created_at ASC
        """)

        rows = cur.fetchall()
        conn.close()

        signals = []
        for r in rows:
            signals.append({
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "leverage": r[3],
                "entry_price": r[4],
                "take_profits": r[5].split(",") if r[5] else [],
                "created_at": r[6],
            })

        return signals

    except Exception as e:
        logger.error(f"❌ Error obteniendo señales pendientes: {e}")
        return []


# ------------------------------------------------------------
# 📌 Marcar una señal como reactivada
# ------------------------------------------------------------
def mark_signal_reactivated(signal_id: int):
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status = 'reactivated',
                reactivated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), signal_id))

        conn.commit()
        conn.close()

        logger.info(f"♻️ Señal {signal_id} marcada como reactivada.")

    except Exception as e:
        logger.error(f"❌ Error en mark_signal_reactivated: {e}")


# ------------------------------------------------------------
# 📌 Actualizar match_ratio en tabla signals
# ------------------------------------------------------------
def update_signal_match_ratio(signal_id: int, match_ratio: float):
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET match_ratio = ?
            WHERE id = ?
        """, (match_ratio, signal_id))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error en update_signal_match_ratio: {e}")


# ------------------------------------------------------------
# 📌 Guardar registro de análisis técnico
# ------------------------------------------------------------
def save_analysis_log(signal_id: int, match_ratio: float, recommendation: str, details: str = ""):
    """
    Guarda un registro histórico del análisis técnico de una señal.
    """

    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signal_analysis_log (signal_id, match_ratio, recommendation, details)
            VALUES (?, ?, ?, ?)
        """, (signal_id, match_ratio, recommendation, details))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error guardando en signal_analysis_log: {e}")
