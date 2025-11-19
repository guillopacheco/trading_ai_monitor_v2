"""
signal_manager_db.py — versión definitiva
------------------------------------------------------------
Gestión de la tabla `signals` unificada y compatible con:

✔ telegram_reader (guarda señales)
✔ technical_brain (análisis técnico inicial y reactivaciones)
✔ signal_reactivation_sync (lectura/modificación)
✔ command_bot (/historial)
✔ main.py

Tabla FINAL esperada:

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    leverage INTEGER DEFAULT 20,
    entry_price REAL,
    tp1 REAL,
    tp2 REAL,
    tp3 REAL,
    tp4 REAL,
    original_message TEXT,
    allowed INTEGER DEFAULT 0,
    overall_trend TEXT,
    suggestion TEXT,
    score REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    reactivated_at TEXT
------------------------------------------------------------
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any

from config import DATABASE_PATH

logger = logging.getLogger("signal_manager_db")


# ============================================================
# 🔌 Conexión segura
# ============================================================
def _connect():
    return sqlite3.connect(
        DATABASE_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False
    )


# ============================================================
# ➕ Guardar nueva señal
# ============================================================
def save_signal(
    symbol: str,
    direction: str,
    leverage: int,
    entry_price: float,
    tp1: float,
    tp2: float,
    tp3: float,
    tp4: float,
    original_message: str,
):
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signals (
                symbol, direction, leverage,
                entry_price, tp1, tp2, tp3, tp4,
                original_message,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            symbol, direction, leverage,
            entry_price, tp1, tp2, tp3, tp4,
            original_message
        ))

        conn.commit()
        conn.close()
        logger.info(f"💾 Señal guardada en DB: {symbol} ({direction}) entry={entry_price}")

    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ============================================================
# 🟡 Señales pendientes de reactivación
# ============================================================
def get_pending_signals_for_reactivation() -> List[Dict[str, Any]]:
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                id, symbol, direction, leverage,
                entry_price, tp1, tp2, tp3, tp4,
                original_message, created_at
            FROM signals
            WHERE status='pending' AND reactivated_at IS NULL
            ORDER BY id DESC
        """)

        rows = cur.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "leverage": r[3],
                "entry_price": r[4],
                "tp1": r[5],
                "tp2": r[6],
                "tp3": r[7],
                "tp4": r[8],
                "original_message": r[9],
                "created_at": r[10],
            })

        return result

    except Exception as e:
        logger.error(f"❌ Error obteniendo señales pendientes: {e}")
        return []


# ============================================================
# ♻️ Marcar como reactivada
# ============================================================
def mark_signal_reactivated(signal_id: int):
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            UPDATE signals
            SET status='reactivated',
                reactivated_at=?
            WHERE id=?
        """, (datetime.utcnow().isoformat(), signal_id))

        conn.commit()
        conn.close()
        logger.info(f"♻️ Señal reactivada en DB (id={signal_id})")

    except Exception as e:
        logger.error(f"❌ Error marcando señal reactivada: {e}")


# ============================================================
# 📜 Obtener historial
# ============================================================
def get_signals(limit: int = 20):
    try:
        conn = _connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage,
                   entry_price, tp1, tp2, tp3, tp4,
                   suggestion, score, status, created_at
            FROM signals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cur.fetchall()
        conn.close()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "leverage": r[3],
                "entry_price": r[4],
                "tp1": r[5],
                "tp2": r[6],
                "tp3": r[7],
                "tp4": r[8],
                "suggestion": r[9],
                "score": r[10],
                "status": r[11],
                "created_at": r[12],
            })

        return result

    except Exception as e:
        logger.error(f"❌ Error en get_signals(): {e}")
        return []
