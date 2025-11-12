import sqlite3
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger("database")

DB_PATH = "trading_ai_monitor.db"

# ================================================================
# 🧱 Inicialización de la base de datos
# ================================================================
def init_database():
    """Crea las tablas necesarias si no existen."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Tabla principal de señales
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair TEXT,
                direction TEXT,
                leverage INTEGER,
                entry REAL,
                take_profits TEXT,
                match_ratio REAL,
                recommendation TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)

        # Tabla para operaciones en curso
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                status TEXT,
                roi REAL,
                last_update TEXT
            )
        """)

        # Tabla de alertas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                last_alert_level INTEGER,
                last_alert_time TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info("✅ Base de datos inicializada correctamente con todas las tablas.")
    except Exception as e:
        logger.error(f"❌ Error al inicializar la base de datos: {e}")


# ================================================================
# 💾 Guardar señal nueva
# ================================================================
async def save_signal(signal: dict):
    """Guarda una señal procesada en la base de datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO signals (pair, direction, leverage, entry, take_profits, match_ratio, recommendation, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.get("pair"),
            signal.get("direction"),
            signal.get("leverage"),
            signal.get("entry"),
            str(signal.get("take_profits")),
            signal.get("match_ratio"),
            signal.get("recommendation"),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ))

        conn.commit()
        conn.close()
        logger.info(f"💾 Señal guardada correctamente en la base de datos: {signal.get('pair')}")
    except Exception as e:
        logger.error(f"❌ Error guardando señal: {e}")


# ================================================================
# 📜 Obtener señales recientes
# ================================================================
def get_signals(limit: int = 10):
    """Recupera las últimas señales almacenadas."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pair, direction, leverage, entry, match_ratio, recommendation, timestamp
            FROM signals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Error obteniendo señales: {e}")
        return []


# ================================================================
# 🧹 Borrar registros antiguos
# ================================================================
def clear_old_records(days: int = 30):
    """Elimina señales más antiguas que X días."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM signals WHERE timestamp < ?", (cutoff.strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        logger.info(f"🧹 {deleted} registros antiguos eliminados correctamente.")
    except Exception as e:
        logger.error(f"❌ Error al eliminar registros antiguos: {e}")


# ================================================================
# 📊 Actualizar estado de operación
# ================================================================
def update_operation_status(symbol: str, status: str, roi: float):
    """Actualiza el estado y ROI actual de una operación abierta."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO operations (symbol, status, roi, last_update)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                status = excluded.status,
                roi = excluded.roi,
                last_update = excluded.last_update
        """, (
            symbol,
            status,
            roi,
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()
        logger.info(f"💾 Operación actualizada: {symbol} -> {status} ({roi:.2f}%)")
    except Exception as e:
        logger.error(f"❌ Error actualizando operación {symbol}: {e}")


# ================================================================
# 🚨 Obtener registro de alerta
# ================================================================
def get_alert_record(symbol: str):
    """Obtiene el último nivel de alerta emitido para una operación."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM alerts WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"❌ Error obteniendo alerta de {symbol}: {e}")
        return None


# ================================================================
# 🚨 Actualizar alerta
# ================================================================
def update_alert_record(symbol: str, level: int, timestamp: str):
    """Actualiza o inserta el registro de alerta más reciente."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO alerts (symbol, last_alert_level, last_alert_time)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                last_alert_level = excluded.last_alert_level,
                last_alert_time = excluded.last_alert_time
        """, (symbol, level, timestamp))

        conn.commit()
        conn.close()
        logger.info(f"🔔 Alerta actualizada para {symbol} nivel {level}")
    except Exception as e:
        logger.error(f"❌ Error actualizando alerta de {symbol}: {e}")
