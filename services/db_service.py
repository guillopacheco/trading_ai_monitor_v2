"""
services/db_service.py
----------------------
Servicio de base de datos SQLite para Trading AI Monitor.
"""

import sqlite3
import json
import logging
import os
from typing import List, Dict, Any

from config import DB_PATH

logger = logging.getLogger("db_service")


# ============================================================
# 🔧 CONEXIÓN
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ============================================================
# 🏗 CREACIÓN DE TABLAS
# ============================================================

def init_db():
    """
    Crea la base de datos y sus tablas si no existen.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    # Tabla principal de señales
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            timestamp INTEGER,
            raw_text TEXT,
            reactivated INTEGER DEFAULT 0
        );
    """)

    # Logs de análisis técnicos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            timestamp INTEGER,
            allowed INTEGER,
            reason TEXT,
            result_json TEXT,
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        );
    """)

    # Tabla de reactivaciones
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reactivations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            reason TEXT,
            timestamp INTEGER,
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        );
    """)

    conn.commit()
    conn.close()
    logger.info(f"🗄 DB inicializada correctamente en {DB_PATH}")


# ============================================================
# 🟦 GUARDAR NUEVA SEÑAL
# ============================================================

def save_new_signal(signal_obj) -> int:
    """
    Guarda una nueva señal en la tabla signals.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO signals (symbol, direction, entry_price, timestamp, raw_text)
        VALUES (?, ?, ?, ?, ?)
    """, (
        signal_obj.symbol,
        signal_obj.direction,
        signal_obj.entry_price,
        signal_obj.timestamp,
        signal_obj.raw_text,
    ))

    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


# ============================================================
# 🟧 CONSULTAR SEÑALES PENDIENTES
# ============================================================

def get_pending_signals() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, symbol, direction, entry_price, timestamp, raw_text
        FROM signals
        WHERE reactivated = 0
        ORDER BY timestamp ASC
    """)

    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "symbol": r[1],
            "direction": r[2],
            "entry_price": r[3],
            "timestamp": r[4],
            "raw_text": r[5],
        })
    return result


# ============================================================
# 🟧 MARCAR COMO REACTIVADA
# ============================================================

def set_signal_reactivated(signal_id: int, reason: str = "Motor A+"):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""UPDATE signals SET reactivated = 1 WHERE id = ?""", (signal_id,))
    cur.execute("""
        INSERT INTO reactivations (signal_id, reason, timestamp)
        VALUES (?, ?, strftime('%s','now'))
    """, (signal_id, reason))

    conn.commit()
    conn.close()


# ============================================================
# 📘 LOGS DE ANÁLISIS
# ============================================================

def add_analysis_log(signal_id: int, timestamp: int, result: dict,
                     allowed: bool, reason: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO analysis_logs (signal_id, timestamp, allowed, reason, result_json)
        VALUES (?, ?, ?, ?, ?)
    """, (
        signal_id,
        timestamp,
        1 if allowed else 0,
        reason,
        json.dumps(result)
    ))

    conn.commit()
    conn.close()


# ============================================================
# 📘 HISTORIAL DE REACTIVACIONES
# ============================================================

def add_reactivation_record(signal_id: int, reason: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO reactivations (signal_id, reason, timestamp)
        VALUES (?, ?, strftime('%s','now'))
    """, (signal_id, reason))

    conn.commit()
    conn.close()


def get_reactivation_records(signal_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, signal_id, reason, timestamp
        FROM reactivations
        WHERE signal_id = ?
        ORDER BY id DESC
    """, (signal_id,))

    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "signal_id": r[1],
            "reason": r[2],
            "timestamp": r[3],
        })
    return result
