"""
db_service.py
--------------
Servicio de acceso a la base de datos SQLite.

Reemplaza completamente cualquier referencia antigua a:
    - signal_manager_db.py
    - signal_manager.py

Provee funciones limpias y centralizadas para:
    - Crear señales
    - Obtener señales pendientes
    - Registrar análisis
    - Guardar logs de posiciones
"""

import sqlite3
from typing import List, Dict, Any, Optional
from config import DB_PATH

import logging
logger = logging.getLogger("db_service")


# ============================================================
# 🔵 CONEXIÓN
# ============================================================
def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ============================================================
# 🔵 INICIALIZACIÓN DE TABLAS
# ============================================================
def init_db():
    conn = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            direction TEXT,
            entry REAL,
            tp_list TEXT,
            sl REAL,
            status TEXT,
            match_ratio REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            match_ratio REAL,
            recommendation TEXT,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS position_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            direction TEXT,
            pnl_pct REAL,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()
    logger.info("🗄 DB inicializada correctamente.")


# ============================================================
# 🔵 CRUD: SEÑALES
# ============================================================
def create_signal(data: Dict[str, Any]) -> Optional[int]:
    """
    Inserta una señal nueva en la base de datos.
    """
    conn = _conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO signals (symbol, direction, entry, tp_list, sl, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            data.get("symbol"),
            data.get("direction"),
            data.get("entry"),
            ",".join(str(t) for t in data.get("tp_list", [])),
            data.get("sl"),
            "pending"
        ])

        signal_id = cursor.lastrowid
        conn.commit()
        return signal_id

    except Exception as e:
        logger.error(f"❌ Error creando señal: {e}")
        return None

    finally:
        conn.close()


def get_pending_signals() -> List[Dict[str, Any]]:
    conn = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, symbol, direction, entry, tp_list, sl
        FROM signals
        WHERE status = 'pending'
    """)

    rows = cursor.fetchall()
    conn.close()

    signals = []
    for r in rows:
        signals.append({
            "id": r[0],
            "symbol": r[1],
            "direction": r[2],
            "entry": r[3],
            "tp_list": [float(x) for x in r[4].split(",") if x],
            "sl": r[5]
        })

    return signals


def set_signal_reactivated(signal_id: int):
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE signals SET status='active', updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, [signal_id])
    conn.commit()
    conn.close()


def set_signal_ignored(signal_id: int):
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE signals SET status='ignored', updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, [signal_id])
    conn.commit()
    conn.close()


def set_signal_match_ratio(signal_id: int, ratio: float):
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE signals SET match_ratio=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, [ratio, signal_id])
    conn.commit()
    conn.close()


# ============================================================
# 🔵 LOGS TÉCNICOS
# ============================================================
def add_analysis_log(signal_id: int, match_ratio: float, recommendation: str, details: str):
    conn = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analysis_logs (signal_id, match_ratio, recommendation, details)
        VALUES (?, ?, ?, ?)
    """, [signal_id, match_ratio, recommendation, details])

    conn.commit()
    conn.close()


def get_logs(limit: int = 20):
    conn = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT signal_id, match_ratio, recommendation, timestamp
        FROM analysis_logs
        ORDER BY id DESC
        LIMIT ?
    """, [limit])

    rows = cursor.fetchall()
    conn.close()

    logs = []
    for r in rows:
        logs.append({
            "signal_id": r[0],
            "match_ratio": r[1],
            "recommendation": r[2],
            "timestamp": r[3],
        })

    return logs


# ============================================================
# 🔵 LOGS DE POSICIONES
# ============================================================
def add_position_log(symbol: str, direction: str, pnl_pct: float, timestamp: str):
    conn = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO position_logs (symbol, direction, pnl_pct, timestamp)
        VALUES (?, ?, ?, ?)
    """, [symbol, direction, pnl_pct, timestamp])

    conn.commit()
    conn.close()
