"""
database.py — versión final unificada (2025-11)
------------------------------------------------------------
Módulo oficial de base de datos para el Trading AI Monitor.

Tablas:
✔ signals
✔ signal_analysis_log
✔ positions (futura expansión)

Completamente compatible con TODA la arquitectura nueva:
- telegram_reader.py
- signal_reactivation_sync.py
- command_bot.py
- trend_system_final
------------------------------------------------------------
"""

import sqlite3
import logging
from datetime import datetime
import os

logger = logging.getLogger("database")

DB_PATH = "trading_ai_monitor.db"


# ============================================================
# 🔧 Conexión segura
# ============================================================

def get_connection():
    """Retorna una conexión segura en modo multithread."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ============================================================
# 🏗️ Inicializar base de datos
# ============================================================

def init_db():
    """Crea las tablas necesarias si no existen."""
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

        # Tabla de posiciones (no usada por ahora, pero lista)
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

        logger.info("✅ Base de datos inicializada correctamente.")

    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")


# ============================================================
# 💾 Guardar señal nueva
# ============================================================

def save_signal(record: dict):
    """
    Guarda una nueva señal proveniente de telegram_reader.
    record = {
        symbol, direction, entry_price, take_profits,
        leverage, match_ratio, recommendation
    }
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signals (
                symbol, direction, leverage,
                entry_price, take_profits,
                match_ratio, recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("symbol"),
            record.get("direction"),
            record.get("leverage", 20),
            record.get("entry_price"),
            ",".join(map(str, record.get("take_profits", []))),
            record.get("match_ratio", 0.0),
            record.get("recommendation", ""),
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ============================================================
# 🔄 Señales pendientes para reactivación
# ============================================================

def get_pending_signals_for_reactivation():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage, entry_price, created_at
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
                "entry_price": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"❌ Error leyendo señales pendientes: {e}")
        return []


# ============================================================
# ♻️ Marcar señal como reactivada
# ============================================================

def mark_signal_reactivated(signal_id: int):
    try:
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

    except Exception as e:
        logger.error(f"❌ Error marcando señal reactivada: {e}")


# ============================================================
# 📝 Guardar log detallado de análisis
# ============================================================

def save_analysis_log(signal_id: int, match_ratio: float, recommendation: str, details: str = ""):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO signal_analysis_log (
                signal_id, match_ratio, recommendation, details
            )
            VALUES (?, ?, ?, ?)
        """, (signal_id, match_ratio, recommendation, details))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"❌ Error al guardar análisis: {e}")


# ============================================================
# 📜 Obtener señales recientes para /historial
# ============================================================

def get_signals(limit: int = 50) -> list:
    """
    Devuelve señales en formato dict — AL FIN CORRECTO.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, symbol, direction, leverage, entry_price,
                   take_profits, match_ratio, recommendation,
                   created_at, status, reactivated_at
            FROM signals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

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
                "created_at": r[8],
                "status": r[9],
                "reactivated_at": r[10],
            })

        return results

    except Exception as e:
        logger.error(f"❌ Error en get_signals(): {e}")
        return []


# ============================================================
# 🧹 Limpieza automática
# ============================================================

def clear_old_records(days: int = 30):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM signals
            WHERE julianday('now') - julianday(created_at) > ?
        """, (days,))

        conn.commit()
        conn.close()
        logger.info(f"🧹 Limpieza completada: señales con más de {days} días eliminadas.")

    except Exception as e:
        logger.error(f"❌ Error en clear_old_records: {e}")