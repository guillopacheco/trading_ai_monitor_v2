"""
services/db_service.py
----------------------
Servicio de base de datos SQLite para Trading AI Monitor v2 (esquema A simple).

Tablas:
    - signals        → Señales recibidas (del canal o manuales)
    - analyses       → Resultados de análisis técnico del Motor A+
    - reactivations  → Historial de reactivaciones
    - errors         → Log de errores de alto nivel

Este módulo está diseñado para ser compatible con:
    - controllers.signal_controller
    - controllers.reactivation_controller
    - core.signal_engine
    - technical_brain_unified
"""

from __future__ import annotations

import os
import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional

from config import DB_PATH

logger = logging.getLogger("db_service")


# ============================================================
# 🔧 CONEXIÓN
# ============================================================

def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión a la base de datos."""
    return sqlite3.connect(DB_PATH)


# ============================================================
# 🏗 CREACIÓN DE TABLAS (ESQUEMA A)
# ============================================================

def init_db() -> None:
    """
    Crea la base de datos y sus tablas si no existen.
    Esquema simple A (signals + analyses + reactivations + errors).
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    # Tabla principal de señales
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            timestamp INTEGER,
            raw_text TEXT,
            reactivated INTEGER DEFAULT 0
        );
        """
    )

    # Resultados de análisis técnico
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            timestamp INTEGER,
            allowed INTEGER,
            confidence REAL,
            match_ratio REAL,
            summary TEXT,
            details_json TEXT,
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        );
        """
    )

    # Historial de reactivaciones
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reactivations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            reason TEXT,
            timestamp INTEGER,
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        );
        """
    )

    # Log de errores
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context TEXT,
            message TEXT,
            timestamp INTEGER
        );
        """
    )

    conn.commit()
    conn.close()
    logger.info(f"🗄 DB inicializada correctamente en {DB_PATH}")
    

# ============================================================
# 🟦 SEÑALES
# ============================================================

def save_new_signal(signal_obj) -> int:
    """
    Guarda una nueva señal en la tabla 'signals'.

    Espera un objeto con atributos:
        - symbol
        - direction
        - entry_price
        - timestamp
        - raw_text
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO signals (symbol, direction, entry_price, timestamp, raw_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            signal_obj.symbol,
            signal_obj.direction,
            getattr(signal_obj, "entry_price", None),
            getattr(signal_obj, "timestamp", None),
            getattr(signal_obj, "raw_text", ""),
        ),
    )

    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_pending_signals() -> List[Dict[str, Any]]:
    """
    Devuelve señales que aún NO han sido reactivadas (reactivated = 0).
    Usado por reactivation_controller.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, symbol, direction, entry_price, timestamp, raw_text
        FROM signals
        WHERE reactivated = 0
        ORDER BY timestamp ASC
        """
    )

    rows = cur.fetchall()
    conn.close()

    result: List[Dict[str, Any]] = []
    for r in rows:
        result.append(
            {
                "id": r[0],
                "symbol": r[1],
                "direction": r[2],
                "entry_price": r[3],
                "timestamp": r[4],
                "raw_text": r[5],
            }
        )
    return result


def set_signal_reactivated(signal_id: int, reason: str = "Motor A+"):
    """
    Marca una señal como reactivada y registra en la tabla reactivations.
    """
    from utils.helpers import now_ts  # evitamos ciclos globales

    ts = now_ts()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("UPDATE signals SET reactivated = 1 WHERE id = ?", (signal_id,))
    cur.execute(
        """
        INSERT INTO reactivations (signal_id, reason, timestamp)
        VALUES (?, ?, ?)
        """,
        (signal_id, reason, ts),
    )

    conn.commit()
    conn.close()


def get_signal_by_id(signal_id: int) -> Optional[Dict[str, Any]]:
    """
    Devuelve una señal por id o None.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, symbol, direction, entry_price, timestamp, raw_text, reactivated
        FROM signals
        WHERE id = ?
        """,
        (signal_id,),
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "symbol": row[1],
        "direction": row[2],
        "entry_price": row[3],
        "timestamp": row[4],
        "raw_text": row[5],
        "reactivated": row[6],
    }


# ============================================================
# 📊 ANALYSIS LOGS (Motor Técnico A+)
# ============================================================

def add_analysis_log(
    signal_id: int,
    timestamp: int,
    result: Dict[str, Any],
    allowed: bool,
    reason: str,
):
    """
    Registra un análisis técnico en la tabla 'analyses'.

    'result' es el dict completo devuelto por el Motor A+.
    Se intenta extraer:
        - confidence
        - match_ratio
        - summary (texto)
    """
    # Valores derivados
    decision = result.get("decision", {})
    metrics = result.get("metrics", {})

    confidence = float(decision.get("confidence", 0.0))
    match_ratio = float(metrics.get("match_ratio", 0.0))
    summary = decision.get("summary", reason)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO analyses (
            signal_id, timestamp, allowed, confidence, match_ratio, summary, details_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_id,
            timestamp,
            1 if allowed else 0,
            confidence,
            match_ratio,
            summary,
            json.dumps(result),
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# ♻️ REACTIVACIONES
# ============================================================

def add_reactivation_record(signal_id: int, reason: str):
    """
    Inserta una reactivación manual/automática adicional.
    (Útil si quieres registrar varios eventos de reactivación).
    """
    from utils.helpers import now_ts

    ts = now_ts()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO reactivations (signal_id, reason, timestamp)
        VALUES (?, ?, ?)
        """,
        (signal_id, reason, ts),
    )

    conn.commit()
    conn.close()


def get_reactivation_records(signal_id: int) -> List[Dict[str, Any]]:
    """
    Devuelve todas las reactivaciones asociadas a una señal.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, signal_id, reason, timestamp
        FROM reactivations
        WHERE signal_id = ?
        ORDER BY id DESC
        """,
        (signal_id,),
    )

    rows = cur.fetchall()
    conn.close()

    result: List[Dict[str, Any]] = []
    for r in rows:
        result.append(
            {
                "id": r[0],
                "signal_id": r[1],
                "reason": r[2],
                "timestamp": r[3],
            }
        )
    return result


# ============================================================
# ⚠️ ERRORES
# ============================================================

def log_error(context: str, message: str, timestamp: Optional[int] = None):
    """
    Registra un error en la tabla 'errors'.
    """
    from utils.helpers import now_ts

    ts = timestamp or now_ts()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO errors (context, message, timestamp)
        VALUES (?, ?, ?)
        """,
        (context, message, ts),
    )

    conn.commit()
    conn.close()
