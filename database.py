# ================================================================
# database.py — VERSIÓN FINALIZADA 2025-12
# Módulo central de persistencia para Trading AI Monitor v2
# ================================================================
import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger("database")

DB_PATH = "trading_ai.db"


# ================================================================
# Conexión
# ================================================================
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ================================================================
# Inicialización de tablas
# ================================================================
def init_db():
    conn = _get_conn()
    cur = conn.cursor()

    # Tabla de señales recibidas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            raw_text TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Logs técnicos asociados a una señal
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            context TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );
    """)

    # Eventos de operación
    cur.execute("""
        CREATE TABLE IF NOT EXISTS operation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Posiciones abiertas localmente (si se requiere)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS open_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            entry_price REAL,
            qty REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Base de datos inicializada correctamente.")


# ================================================================
# -------------------- SECCIÓN: SEÑALES --------------------------
# ================================================================

def save_signal(payload: dict) -> int:
    """
    Inserta una nueva señal proveniente del canal VIP.
    """
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO signals (symbol, direction, raw_text, status)
        VALUES (?, ?, ?, 'pending')
    """, (
        payload.get("symbol"),
        payload.get("direction"),
        payload.get("raw_text")
    ))

    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return new_id


def get_pending_signals_for_reactivation() -> list:
    """
    Devuelve todas las señales cuyo estado = 'pending'.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM signals
        WHERE status = 'pending'
        ORDER BY id ASC
    """)

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    return rows


def mark_signal_reactivated(signal_id: int):
    """
    Cambia estado → 'reactivated'
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE signals
        SET status = 'reactivated'
        WHERE id = ?
    """, (signal_id,))
    conn.commit()
    conn.close()


# ================================================================
# --------- SECCIÓN: LOGS DE ANÁLISIS TÉCNICO --------------------
# ================================================================

def save_analysis_log(signal_id: int, context: str, analysis_json: dict):
    """
    Guarda el dict completo del análisis técnico (JSON serializado).
    """
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO analysis_logs (signal_id, context, analysis_json)
        VALUES (?, ?, ?)
    """, (
        signal_id,
        context,
        json.dumps(analysis_json)
    ))

    conn.commit()
    conn.close()


# ================================================================
# ------- SECCIÓN: OPERACIONES (EVENTOS Y POSICIONES) ------------
# ================================================================

def save_operation_event(symbol: str, side: str, event_type: str, details: dict):
    """
    Registra un evento relacionado con una operación.
    """
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO operation_events (symbol, side, event_type, details_json)
        VALUES (?, ?, ?, ?)
    """, (
        symbol.upper(),
        side.lower(),
        event_type,
        json.dumps(details)
    ))

    conn.commit()
    conn.close()


def get_open_positions_by_symbol(symbol: str) -> list:
    """
    Devuelve las posiciones abiertas localmente del símbolo.
    """
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM open_positions
        WHERE symbol = ?
    """, (symbol.upper(),))

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    return rows


# FUTURO: podrías agregar update_position, remove_position, etc.


# ================================================================
# Debug helper (opcional)
# ================================================================
def debug_dump():
    """
    Imprime un resumen de tablas.
    """
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM signals")
    signals = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM analysis_logs")
    logs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM operation_events")
    ops = cur.fetchone()[0]

    logger.info(f"📊 DEBUG DB → Signals={signals}, Logs={logs}, Ops={ops}")

    conn.close()
