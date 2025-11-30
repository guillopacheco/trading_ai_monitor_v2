"""
services/db_service.py
----------------------
Servicio de base de datos SQLite para Trading AI Monitor.

Maneja:
    - señales recibidas
    - análisis técnicos
    - estado de reactivación
    - logs
"""

from __future__ import annotations
import sqlite3
import json
import logging
import os
from typing import List, Dict, Any, Optional

from config import DB_PATH

logger = logging.getLogger("db_service")


# ============================================================
# 🔧 CONEXIÓN Y CREACIÓN DE TABLAS
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


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
            entry REAL,
            timestamp INTEGER,
            raw_text TEXT,
            reactivated INTEGER DEFAULT 0
        );
    """)

    # Logs del motor de análisis (historial completo)
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

    # Señales reactivadas (histórico)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reactivations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            timestamp INTEGER,
            reason TEXT,
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS reactivations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        reason TEXT,
        timestamp INTEGER
    )
""")

    conn.commit()
    conn.close()

    logger.info(f"🗄 DB inicializada correctamente en {DB_PATH}")


# ============================================================
# 🟦 GUARDAR NUEVA SEÑAL
# ============================================================

def save_new_signal(signal_obj) -> int:
    """
    Inserta una nueva señal en la tabla 'signals'.
    Retorna el ID asignado.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO signals (symbol, direction, entry, timestamp, raw_text)
        VALUES (?, ?, ?, ?, ?)
    """, (
        signal_obj.symbol,
        signal_obj.direction,
        signal_obj.entry,
        signal_obj.timestamp,
        signal_obj.raw_text,
    ))

    conn.commit()
    signal_id = cur.lastrowid
    conn.close()

    return signal_id


# ============================================================
# 🟧 GUARDAR ANÁLISIS DEL MOTOR
# ============================================================

def add_analysis_log(signal_id: int, timestamp: int, result: dict,
                     allowed: bool, reason: str):
    """
    Guarda un log de análisis técnico completo en formato JSON.
    """
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
# 🟨 OBTENER SEÑALES PENDIENTES DE REACTIVACIÓN
# ============================================================

def get_pending_signals() -> List[Any]:
    """
    Retorna todas las señales que NO han sido reactivadas.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, symbol, direction, entry, timestamp, raw_text
        FROM signals
        WHERE reactivated = 0
        ORDER BY timestamp ASC
    """)

    rows = cur.fetchall()
    conn.close()

    signals = []
    for r in rows:
        signals.append(_make_signal_obj(r))

    return signals


# ============================================================
# 🟨 MARCAR SEÑAL COMO REACTIVADA
# ============================================================

def set_signal_reactivated(signal_id: int, reason: str = "Motor A+"):
    """
    Marca una señal como reactivada y guarda un registro en 'reactivations'.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE signals SET reactivated = 1
        WHERE id = ?
    """, (signal_id,))

    cur.execute("""
        INSERT INTO reactivations (signal_id, timestamp, reason)
        VALUES (?, strftime('%s','now'), ?)
    """, (signal_id, reason))

    conn.commit()
    conn.close()


# ============================================================
# 🟩 OBTENER HISTORIAL COMPLETO DE ANÁLISIS
# ============================================================

def get_logs_for_signal(signal_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp, allowed, reason, result_json
        FROM analysis_logs
        WHERE signal_id = ?
        ORDER BY timestamp ASC
    """, (signal_id,))

    rows = cur.fetchall()
    conn.close()

    logs = []
    for ts, allowed, reason, result_json in rows:
        logs.append({
            "timestamp": ts,
            "allowed": bool(allowed),
            "reason": reason,
            "result": json.loads(result_json or "{}")
        })

    return logs


# ============================================================
# 🔧 UTILIDAD: construir objeto de señal
# ============================================================

def _make_signal_obj(row):
    """
    Crea un objeto simple que imita la estructura utilizada por la aplicación.
    """

    class SignalObj:
        id: int
        symbol: str
        direction: str
        entry: float
        timestamp: int
        raw_text: str

        def __init__(self, id, symbol, direction, entry, timestamp, raw_text):
            self.id = id
            self.symbol = symbol
            self.direction = direction
            self.entry = entry
            self.timestamp = timestamp
            self.raw_text = raw_text

    return SignalObj(*row)

# =======================================================
# 🟦 REACTIVACIONES (nueva tabla: reactivations)
# =======================================================
def add_reactivation_record(signal_id: int, reason: str):
    """Registrar un evento de reactivación."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO reactivations(signal_id, reason, timestamp)
            VALUES (?, ?, strftime('%s', 'now'))
        """, (signal_id, reason))
        conn.commit()


def get_reactivation_records(signal_id: int):
    """Obtener historial de reactivaciones de una señal."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, signal_id, reason, timestamp
            FROM reactivations
            WHERE signal_id = ?
            ORDER BY id DESC
        """, (signal_id,)).fetchall()
        return rows

