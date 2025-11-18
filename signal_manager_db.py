"""
signal_manager_db.py
------------------------------------------------------------
Capa de acceso a la base de datos:

- Guardar señales
- Leer señales pendientes
- Marcar reactivaciones

Compatible con la tabla `signals` FINAL:

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    leverage INTEGER DEFAULT 20,
    entry_price REAL,
    take_profits TEXT,
    match_ratio REAL DEFAULT 0,
    recommendation TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    reactivated_at TEXT,
    status TEXT DEFAULT 'pending'
------------------------------------------------------------
"""

import sqlite3
import logging
from typing import List, Dict, Any
from datetime import datetime

from config import DATABASE_PATH

logger = logging.getLogger("signal_manager_db")


# ============================================================
# 🔌 Conexión segura
# ============================================================
def _connect():
    return sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)


# ============================================================
# ➕ Guardar nueva señal
# ============================================================
def save_signal(symbol: str, direction: str, leverage: int, entry_price: float,
                take_profits: str, match_ratio: float, recommendation: str):

    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signals (
                symbol, direction, leverage, entry_price,
                take_profits, match_ratio, recommendation, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (symbol, direction, leverage, entry_price,
              take_profits, match_ratio, recommendation))

        conn.commit()
        conn.close()

        logger.info(f"💾 Señal guardada: {symbol} {direction} entry={entry_price}")

    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ============================================================
# 🟡 Señales pendientes de reactivación
# ============================================================
def get_pending_signals_for_reactivation():
    """
    Devuelve señales donde:
    - status = 'pending'
    - reactivated_at IS NULL
    """

    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                id, symbol, direction, leverage,
                entry_price, take_profits, match_ratio,
                recommendation, created_at
            FROM signals
            WHERE status = 'pending' AND reactivated_at IS NULL
            ORDER BY id DESC
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
                "take_profits": r[5],
                "match_ratio": r[6],
                "recommendation": r[7],
                "created_at": r[8],
            })

        return signals

    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes: {e}")
        return []


# ============================================================
# ♻️ Marcar señal como reactivada
# ============================================================
def mark_signal_reactivated(signal_id: int):
    """
    Setea reactivated_at = NOW() y status = 'reactivated'
    """

    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status='reactivated',
                reactivated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), signal_id))

        conn.commit()
        conn.close()

        logger.info(f"♻️ Señal marcada como reactivada (id={signal_id})")

    except Exception as e:
        logger.error(f"❌ Error actualizando reactivación: {e}")
