"""
signal_manager_db.py
------------------------------------------------------------
Capa de acceso a base de datos para señales + reactivación.

Compatible con la estructura actual:

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT,
    direction TEXT,
    leverage INTEGER,
    entry_price REAL,
    take_profits TEXT,
    match_ratio REAL,
    recommendation TEXT,
    timestamp TEXT,
    status TEXT DEFAULT 'pending',
    reactivated INTEGER DEFAULT 0

------------------------------------------------------------
"""

import sqlite3
import logging
from typing import List, Dict, Any

from config import DATABASE_PATH

logger = logging.getLogger("signal_manager_db")


# ============================================================
# 🔌 Conexión básica
# ============================================================
def _connect():
    return sqlite3.connect(DATABASE_PATH)


# ============================================================
# 📥 Guardar señal nueva
# ============================================================
def save_signal_db(signal: Dict[str, Any]):
    """Guardar una señal nueva en la tabla signals."""
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO signals (
                pair, direction, leverage, entry_price,
                take_profits, match_ratio, recommendation,
                timestamp, status, reactivated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal["pair"],
                signal["direction"],
                signal.get("leverage", 20),
                signal["entry_price"],
                signal.get("take_profits", ""),
                signal.get("match_ratio", 0.0),
                signal.get("recommendation", ""),
                signal.get("timestamp"),
                signal.get("status", "pending"),
                signal.get("reactivated", 0),
            ),
        )

        conn.commit()
        conn.close()
        logger.info(f"💾 Señal guardada en DB: {signal['pair']}")

    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ============================================================
# 📤 Obtener señales pendientes para reactivación
# ============================================================
def get_pending_signals_for_reactivation() -> List[Dict[str, Any]]:
    """Devuelve señales con status='pending' y reactivated=0."""
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT 
                id, pair, direction, leverage, entry_price,
                take_profits, match_ratio, recommendation,
                timestamp, status, reactivated
            FROM signals
            WHERE status='pending'
              AND reactivated=0
            ORDER BY timestamp DESC
            """
        )

        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "leverage": r[3],
                "entry_price": r[4],
                "take_profits": r[5],
                "match_ratio": r[6],
                "recommendation": r[7],
                "timestamp": r[8],
                "status": r[9],
                "reactivated": r[10],
            })

        return results

    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes para reactivación: {e}")
        return []


# ============================================================
# 🔁 Marcar señal como reactivada
# ============================================================
def mark_signal_reactivated(signal_id: int):
    """Actualiza el estado de una señal como reactivada."""
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE signals
            SET reactivated=1,
                status='reactivated'
            WHERE id=?
            """,
            (signal_id,),
        )

        conn.commit()
        conn.close()
        logger.info(f"♻️ Señal marcada como reactivada (ID={signal_id})")

    except Exception as e:
        logger.error(f"❌ Error marcando señal reactivada: {e}")
