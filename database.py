# database.py - CORRECCIÓN COMPLETA

"""
Sistema de base de datos mejorado - CON NOTIFICACIONES
"""
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class TradingDatabase:
    """Manejador de base de datos de trading - MEJORADO Y CORREGIDO"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        """Inicializa la base de datos con tablas necesarias - CORREGIDO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabla de señales - ESTRUCTURA CORREGIDA
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,  -- ✅ COLUMNA AGREGADA
                        pair TEXT NOT NULL,    -- ✅ MANTENER PARA COMPATIBILIDAD
                        direction TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        stop_loss REAL,
                        take_profit_1 REAL,
                        take_profit_2 REAL, 
                        take_profit_3 REAL,
                        take_profit_4 REAL,
                        leverage INTEGER DEFAULT 20,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        analysis_data TEXT,
                        signal_data TEXT
                    )
                ''')
                
                # Tabla de operaciones (para seguimiento)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_id INTEGER,
                        symbol TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        current_price REAL,
                        position_size REAL,
                        leverage INTEGER,
                        pnl_percentage REAL DEFAULT 0,
                        status TEXT DEFAULT 'open',
                        opened_at TEXT NOT NULL,
                        closed_at TEXT,
                        close_reason TEXT,
                        FOREIGN KEY (signal_id) REFERENCES signals (id)
                    )
                ''')
                
                # ✅ MIGRACIÓN: Agregar columna symbol si no existe
                cursor.execute("PRAGMA table_info(signals)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'symbol' not in columns:
                    logger.info("🔄 Actualizando estructura de la tabla signals...")
                    cursor.execute('ALTER TABLE signals ADD COLUMN symbol TEXT')
                    # Copiar datos de 'pair' a 'symbol' para registros existentes
                    cursor.execute('UPDATE signals SET symbol = pair WHERE symbol IS NULL')
                    conn.commit()
                    logger.info("✅ Estructura de tabla signals actualizada")
                
                conn.commit()
                logger.info("✅ Base de datos inicializada correctamente")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise

    def save_signal(self, signal_data: Dict, analysis_data: Dict) -> int:
        """Guarda señal en BD y notifica - CORREGIDO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                # ✅ CORRECCIÓN: Insertar en ambas columnas symbol y pair para compatibilidad
                cursor.execute('''
                    INSERT INTO signals (
                        symbol, pair, direction, entry_price, stop_loss,
                        take_profit_1, take_profit_2, take_profit_3, take_profit_4,
                        leverage, created_at, updated_at, analysis_data, signal_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_data['pair'],  # symbol
                    signal_data['pair'],  # pair (para compatibilidad)
                    signal_data['direction'],
                    signal_data['entry'],
                    signal_data.get('stop_loss'),
                    signal_data.get('take_profits', [])[0] if signal_data.get('take_profits') else None,
                    signal_data.get('take_profits', [])[1] if len(signal_data.get('take_profits', [])) > 1 else None,
                    signal_data.get('take_profits', [])[2] if len(signal_data.get('take_profits', [])) > 2 else None,
                    signal_data.get('take_profits', [])[3] if len(signal_data.get('take_profits', [])) > 3 else None,
                    signal_data.get('leverage', 20),
                    current_time,
                    current_time,
                    str(analysis_data),
                    str(signal_data)
                ))
                
                signal_id = cursor.lastrowid
                conn.commit()
                
                # ✅ CORRECCIÓN: Usar asyncio.create_task para llamadas async
                asyncio.create_task(
                    self._send_db_notification(
                        signal_id, 
                        signal_data['pair'], 
                        'created', 
                        'Señal guardada en BD'
                    )
                )
                
                logger.info(f"✅ Señal {signal_id} guardada en base de datos: {signal_data['pair']}")
                return signal_id
                
        except Exception as e:
            logger.error(f"❌ Error guardando señal: {e}")
            return None

    def update_signal_status(self, signal_id: int, status: str, update_data: Dict = None):
        """Actualiza estado de señal y notifica - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                # Obtener símbolo para la notificación
                cursor.execute('SELECT symbol FROM signals WHERE id = ?', (signal_id,))
                result = cursor.fetchone()
                symbol = result[0] if result else "UNKNOWN"
                
                cursor.execute('''
                    UPDATE signals 
                    SET status = ?, updated_at = ?, analysis_data = ?
                    WHERE id = ?
                ''', (
                    status,
                    current_time,
                    str(update_data) if update_data else None,
                    signal_id
                ))
                
                conn.commit()
                
                # ✅ NUEVO: Enviar notificación de actualización
                asyncio.create_task(
                    self._send_db_notification(
                        signal_id, 
                        symbol, 
                        status, 
                        f"Actualizado a {status}"
                    )
                )
                
                logger.info(f"✅ Señal {signal_id} actualizada a estado: {status}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error actualizando señal {signal_id}: {e}")
            return False

    def get_recent_signals(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Obtiene señales recientes - CORREGIDO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE created_at > ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (time_threshold, limit))
                
                signals = []
                for row in cursor.fetchall():
                    signal = dict(row)
                    # ✅ CORRECCIÓN: Asegurar que 'symbol' existe
                    if 'symbol' not in signal or not signal['symbol']:
                        # Usar 'pair' como fallback
                        signal['symbol'] = signal.get('pair', 'UNKNOWN')
                    signals.append(signal)
                    
                return signals
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo señales recientes: {e}")
            return []

    def get_signal_stats(self, hours: int = 24) -> Dict:
        """Obtiene estadísticas de señales"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                # Total señales
                cursor.execute('''
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                           SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                           SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                    FROM signals 
                    WHERE created_at > ?
                ''', (time_threshold,))
                
                result = cursor.fetchone()
                stats = {
                    'total': result[0] if result else 0,
                    'confirmed': result[1] if result else 0,
                    'rejected': result[2] if result else 0,
                    'pending': result[3] if result else 0
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}

    def cleanup_old_signals(self, days_to_keep: int = 7):
        """Limpia señales antiguas de la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
                
                cursor.execute('DELETE FROM signals WHERE created_at < ?', (cutoff_date,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"🗑️ {deleted_count} señales antiguas eliminadas")
                else:
                    logger.info("✅ No hay señales antiguas para eliminar")
                    
        except Exception as e:
            logger.error(f"❌ Error limpiando señales antiguas: {e}")

    def create_operation(self, signal_id: int, operation_data: Dict) -> int:
        """Crea una nueva operación para seguimiento"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO operations (
                        signal_id, symbol, direction, entry_price, 
                        current_price, position_size, leverage, opened_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_id,
                    operation_data['symbol'],
                    operation_data['direction'],
                    operation_data['entry_price'],
                    operation_data['entry_price'],  # current_price inicial = entry_price
                    operation_data.get('position_size', 0),
                    operation_data.get('leverage', 20),
                    current_time
                ))
                
                operation_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ Operación {operation_id} creada para señal {signal_id}")
                return operation_id
                
        except Exception as e:
            logger.error(f"❌ Error creando operación: {e}")
            return None

    def update_operation_price(self, operation_id: int, current_price: float):
        """Actualiza precio actual de operación y calcula PnL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener datos de la operación
                cursor.execute(
                    'SELECT entry_price, direction FROM operations WHERE id = ?', 
                    (operation_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return False
                    
                entry_price, direction = result
                
                # Calcular PnL porcentual
                if direction == 'LONG':
                    pnl_percentage = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_percentage = ((entry_price - current_price) / entry_price) * 100
                
                cursor.execute('''
                    UPDATE operations 
                    SET current_price = ?, pnl_percentage = ?
                    WHERE id = ?
                ''', (current_price, pnl_percentage, operation_id))
                
                conn.commit()
                
                # ✅ NUEVO: Verificar si necesita alerta de pérdida
                if pnl_percentage <= -30:
                    asyncio.create_task(
                        self._check_loss_alert(operation_id, pnl_percentage)
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Error actualizando operación {operation_id}: {e}")
            return False

    def close_operation(self, operation_id: int, close_reason: str):
        """Cierra una operación y notifica - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE operations 
                    SET status = 'closed', closed_at = ?, close_reason = ?
                    WHERE id = ?
                ''', (current_time, close_reason, operation_id))
                
                conn.commit()
                
                # ✅ NUEVO: Enviar notificación de cierre
                cursor.execute('SELECT symbol FROM operations WHERE id = ?', (operation_id,))
                result = cursor.fetchone()
                symbol = result[0] if result else "UNKNOWN"
                
                asyncio.create_task(
                    self._send_db_notification(
                        operation_id, 
                        symbol, 
                        'closed', 
                        f"Cerrada: {close_reason}"
                    )
                )
                
                logger.info(f"✅ Operación {operation_id} cerrada: {close_reason}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error cerrando operación {operation_id}: {e}")
            return False

    # === NUEVOS MÉTODOS MEJORADOS ===

    async def _send_db_notification(self, record_id: int, symbol: str, action: str, result: str):
        """Envía notificación de BD - NUEVO MÉTODO"""
        try:
            from notifier import telegram_notifier
            await telegram_notifier.send_db_update_notification(str(record_id), symbol, action, result)
        except Exception as e:
            logger.error(f"❌ Error enviando notificación BD: {e}")

    async def _check_loss_alert(self, operation_id: int, pnl_percentage: float):
        """Verifica y envía alerta de pérdida - NUEVO MÉTODO"""
        try:
            from notifier import telegram_notifier
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, entry_price, current_price, direction 
                    FROM operations WHERE id = ?
                ''', (operation_id,))
                
                result = cursor.fetchone()
                if not result:
                    return
                    
                operation = dict(result)
                
                # Determinar recomendación basada en la pérdida
                if pnl_percentage <= -70:
                    recommendation = "CONSIDERAR CIERRE INMEDIATO"
                elif pnl_percentage <= -50:
                    recommendation = "EVALUAR REVERSIÓN O CIERRE"
                elif pnl_percentage <= -30:
                    recommendation = "MONITOREAR TENDENCIA"
                else:
                    return
                
                await telegram_notifier.send_loss_alert(
                    symbol=operation['symbol'],
                    loss_percentage=abs(pnl_percentage),
                    current_price=operation['current_price'],
                    entry_price=operation['entry_price'],
                    recommendation=recommendation
                )
                
        except Exception as e:
            logger.error(f"❌ Error verificando alerta de pérdida: {e}")

# Instancia global
trading_db = TradingDatabase()