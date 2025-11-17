"""
signal_manager_db.py
-----------------------------------------------------
Capa de acceso específica para señales usadas por el
sistema de reactivación automática.

Esta capa centraliza:

✔ señales pendientes para reactivación
✔ marcar señal como reactivada
✔ evitar duplicación con signal_manager.py
-----------------------------------------------------
"""

import sqlite3
from datetime import datetime
from config import DATABASE_PATH

# -----------------------------------------------------
# 📌 Utilidad interna: conexión segura
# -----------------------------------------------------
def _connect():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


# -----------------------------------------------------
# 📌 Obtener señales pendientes para reactivación
# -----------------------------------------------------
def get_pending_signals_for_reactivation():
    """
    Devuelve señales con recomendaciones que pueden reactivarse:
    - "esperar" o "descartar" (dependiendo del texto)
    - que no hayan sido reactivadas ya
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, pair AS symbol, direction, leverage, entry
        FROM signals
        WHERE reactivated = 0
          AND (
                LOWER(recommendation) LIKE '%esperar%'
             OR LOWER(recommendation) LIKE '%descartar%'
          )
        ORDER BY timestamp DESC
        LIMIT 50
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
        })
    return signals


# -----------------------------------------------------
# 📌 Marcar una señal como reactivada
# -----------------------------------------------------
def mark_signal_reactivated(signal_id: int):
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE signals
        SET reactivated = 1,
            reactivation_timestamp = ?
        WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), signal_id))

    conn.commit()
    conn.close()
