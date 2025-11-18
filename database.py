"""
database.py
----------------------------------------------------------------
Módulo unificado para manejo de base de datos SQLite.
Compatible con toda la arquitectura moderna del proyecto.

Tablas incluidas:
- signals
- signal_analysis_log
- positions (futura expansión)
----------------------------------------------------------------
"""

import sqlite3
import logging
from datetime import datetime
import os

logger = logging.getLogger("database")

DB_PATH = "trading_ai_monitor.db"


# ================================================================
# 🔧 Conexión segura
# ================================================================
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ================================================================
# 🏗️ Inicializar base de datos
# ================================================================
def init_database():
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Tabla principal de señales
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signals (
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
            );
        """)

        # Historial detallado de análisis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signal_analysis_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                match_ratio REAL,
                recommendation TEXT,
                details TEXT,
                FOREIGN KEY(signal_id) REFERENCES signals(id)
            );
        """)

        # Tabla futura (opcional)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                size REAL,
                leverage INTEGER,
                opened_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'open'
            );
        """)

        conn.commit()
        conn.close()

        logger.info("✅ Base de datos inicializada correctamente con todas las tablas.")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")

def save_signal(record: dict):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO signals (symbol, direction, leverage, entry_price, take_profits, match_ratio, recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        record.get("symbol"),
        record.get("direction"),
        record.get("leverage", 20),
        record.get("entry_price"),
        ",".join(map(str, record.get("take_profits", []))),
        record.get("match_ratio", 0.0),
        record.get("recommendation")
    ))

    conn.commit()
    conn.close()

def get_pending_signals_for_reactivation():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, symbol, direction, leverage, entry_price
        FROM signals
        WHERE status = 'pending'
          AND entry_price IS NOT NULL
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "symbol": r[1],
            "direction": r[2],
            "leverage": r[3],
            "entry_price": r[4]
        }
        for r in rows
    ]

def mark_signal_reactivated(signal_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE signals
        SET status = 'reactivated',
            reactivated_at = ?
        WHERE id = ?
    """, (datetime.utcnow().isoformat(), signal_id))

    conn.commit()
    conn.close()

def save_analysis_log(signal_id: int, match_ratio: float, recommendation: str, details: str = ""):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO signal_analysis_log (signal_id, match_ratio, recommendation, details)
        VALUES (?, ?, ?, ?)
    """, (signal_id, match_ratio, recommendation, details))

    conn.commit()
    conn.close()

# ============================================================
# 📄 Obtener todas las señales (para /historial)
# ============================================================
def get_signals(limit: int = 50) -> list:
    """
    Devuelve las señales más recientes desde la tabla signals.
    Usada por /historial en command_bot.py
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT id, pair, direction, leverage, entry,
                   take_profits, match_ratio, recommendation,
                   timestamp, status
            FROM signals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()

        return rows

    except Exception as e:
        logger.error(f"❌ Error en get_signals: {e}")
        return []


# ============================================================
# 🧹 Limpieza automática de registros viejos
# ============================================================
def clear_old_records(days: int = 30):
    """
    Elimina señales con más de N días.
    Usado por command_bot.py en /limpiar o de forma automática.
    """

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute(f"""
            DELETE FROM signals
            WHERE julianday('now') - julianday(timestamp) > ?
        """, (days,))
        conn.commit()
        conn.close()
        logger.info(f"🧹 Limpieza completada: señales con más de {days} días eliminadas.")
    except Exception as e:
        logger.error(f"❌ Error en clear_old_records: {e}")
