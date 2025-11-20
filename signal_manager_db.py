"""
signal_manager_db.py — Módulo oficial para gestionar señales en SQLite
-----------------------------------------------------------------------

Version corregida 2025-11-20
Compatible con:
✔ telegram_reader.py
✔ signal_reactivation_sync.py
✔ trend_system_final.py
✔ database.py

FUNCIONES INCLUIDAS:
✔ save_new_signal()
✔ get_pending_signals()
✔ get_pending_signals_for_reactivation()
✔ update_signal_reactivation_status()
✔ mark_signal_reactivated()
✔ save_analysis_log()
✔ update_signal_match_ratio()
"""

import sqlite3
import logging
from datetime import datetime
from config import DATABASE_PATH as DATABASE_FILE

logger = logging.getLogger("signal_manager_db")


# ------------------------------------------------------------
# 🔌 Conexión centralizada
# ------------------------------------------------------------
def _get_conn():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)


# ============================================================
# 1) GUARDAR NUEVA SEÑAL
# ============================================================
def save_new_signal(symbol: str, direction: str, entry_price: float,
                    leverage: int, take_profits: list, raw_text: str):
    """
    Guarda una señal nueva en la tabla signals.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signals (symbol, direction, entry_price, leverage,
                                 take_profits, raw_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            symbol,
            direction,
            entry_price,
            leverage,
            ",".join(map(str, take_profits)),
            raw_text,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error guardando nueva señal: {e}")


# ============================================================
# 2) OBTENER SEÑALES PENDIENTES
# ============================================================
def get_pending_signals():
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage, entry_price, take_profits, created_at
            FROM signals
            WHERE status = 'pending'
              AND entry_price IS NOT NULL
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
                "created_at": r[6]
            })

        return signals

    except Exception as e:
        logger.error(f"❌ Error obteniendo señales pendientes: {e}")
        return []


# ============================================================
# 3) OBTENER SEÑALES PARA REACTIVACIÓN
# ============================================================
def get_pending_signals_for_reactivation():
    """
    Señales con status='pending' que necesitan
    ser evaluadas por signal_reactivation_sync.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage, entry_price,
                   take_profits, created_at
            FROM signals
            WHERE status = 'pending'
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
                "created_at": r[6]
            })

        return signals

    except Exception as e:
        logger.error(f"❌ Error en get_pending_signals_for_reactivation: {e}")
        return []


# ============================================================
# 4) ACTUALIZAR ESTADO DESPUÉS DE REACTIVACIÓN
# ============================================================
def update_signal_reactivation_status(signal_id: int, status: str):
    """
    Actualiza el campo status tras reactivación:
    status ∈ {'pending', 'reactivated', 'ignored'}
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status = ?, reactivated_at = ?
            WHERE id = ?
        """, (
            status,
            datetime.utcnow().isoformat(),
            signal_id
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error en update_signal_reactivation_status: {e}")


# ============================================================
# 5) LOG DE ANÁLISIS
# ============================================================
def save_analysis_log(signal_id: int, match_ratio: float,
                      recommendation: str, details: str = ""):
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
        logger.error(f"❌ Error guardando signal_analysis_log: {e}")


# ============================================================
# 6) ACTUALIZAR MATCH RATIO
# ============================================================
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
