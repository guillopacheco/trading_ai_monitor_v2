"""
Gestión de base de datos SQLite para registro de señales y operaciones - MEJORADO
"""
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import DATABASE_PATH
import os

logger = logging.getLogger(__name__)

class TradingDatabase:
    """Manejador de base de datos para el sistema de trading - MEJORADO"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()
    
    def reconnect(self):
        """
        Método para reconexión - requerido por el sistema de autoreconexión
        """
        try:
            # Para SQLite, la reconexión es automática
            # Solo verificamos que la base de datos esté accesible
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
            logger.info("✅ Base de datos reconectada/verificada")
            return True
        except Exception as e:
            logger.error(f"❌ Error verificando base de datos: {e}")
            return False
    
    def test_connection(self):
        """
        Método para test de conexión - requerido por el sistema de autoreconexión
        """
        try:
            # Para SQLite, simplemente verificamos que la base de datos esté accesible
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
            return True
        except Exception as e:
            logger.error(f"❌ Error en test de conexión BD: {e}")
            return False
    
    @property
    def is_connected(self):
        """Propiedad para verificar conexión - requerida por autoreconexión"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
            return True
        except Exception as e:
            logger.error(f"❌ Error en verificación de conexión BD: {e}")
            return False
    
    def _init_database(self):
        """Inicializa la base de datos con las tablas necesarias - MEJORADO"""
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabla de señales - MEJORADA CON LEVERAGE
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pair TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        tp1 REAL,
                        tp2 REAL,
                        tp3 REAL,
                        tp4 REAL,
                        leverage INTEGER DEFAULT 20,  -- ✅ NUEVO CAMPO
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'received',
                        confirmation_status TEXT,
                        match_percentage REAL,
                        confidence TEXT,
                        original_message TEXT,
                        analysis_summary TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabla de análisis - MEJORADA
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS signal_analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_id INTEGER,
                        timeframe TEXT,
                        trend TEXT,
                        rsi REAL,
                        rsi_status TEXT,
                        macd_signal TEXT,
                        macd_line REAL,
                        macd_histogram REAL,
                        atr REAL,
                        atr_status TEXT,
                        atr_multiplier REAL,
                        close_price REAL,
                        analysis_timestamp DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES signals (id) ON DELETE CASCADE
                    )
                ''')
                
                # Tabla de divergencias - MEJORADA
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS divergences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_id INTEGER,
                        type TEXT,
                        indicator TEXT,
                        timeframe TEXT,
                        strength TEXT,
                        confidence REAL DEFAULT 0.5,
                        price_swing_low REAL,
                        price_swing_high REAL,
                        indicator_swing_low REAL,
                        indicator_swing_high REAL,
                        detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES signals (id) ON DELETE CASCADE
                    )
                ''')
                
                # Tabla de operaciones (para futura implementación)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        signal_id INTEGER,
                        entry_price REAL,
                        exit_price REAL,
                        roi REAL,
                        position_size REAL,
                        open_time DATETIME,
                        close_time DATETIME,
                        status TEXT DEFAULT 'open',
                        action_type TEXT,
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (signal_id) REFERENCES signals (id) ON DELETE SET NULL
                    )
                ''')
                
                # Índices para mejor performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_pair ON signals(pair)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_signal_id ON signal_analysis(signal_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_divergences_signal_id ON divergences(signal_id)')
                
                conn.commit()
                logger.info("✅ Base de datos inicializada correctamente")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise
    
    def save_signal(self, signal_data: Dict, analysis_result: Dict) -> Optional[int]:
        """Guarda una señal y su análisis en la base de datos - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Preparar datos de la señal
                confirmation_result = analysis_result.get('confirmation_result', {})
                analysis_summary = analysis_result.get('analysis_summary', {})
                
                # Insertar señal principal (AGREGAR LEVERAGE)
                cursor.execute('''
                    INSERT INTO signals (
                        pair, direction, entry_price, tp1, tp2, tp3, tp4, leverage,
                        status, confirmation_status, match_percentage, confidence,
                        original_message, analysis_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_data.get('pair', 'UNKNOWN'),
                    signal_data.get('direction', 'UNKNOWN'),
                    signal_data.get('entry', 0.0),
                    signal_data.get('tp1'),
                    signal_data.get('tp2'),
                    signal_data.get('tp3'),
                    signal_data.get('tp4'),
                    signal_data.get('leverage', 20),  # ✅ NUEVO
                    'received',
                    confirmation_result.get('status', 'UNKNOWN'),
                    confirmation_result.get('match_percentage', 0.0),
                    confirmation_result.get('confidence', 'BAJA'),
                    signal_data.get('message_text', ''),
                    json.dumps(analysis_summary) if analysis_summary else None
                ))
                
                signal_id = cursor.lastrowid
                
                # Guardar análisis por timeframe
                technical_analysis = analysis_result.get('technical_analysis', {})
                for tf_key, analysis in technical_analysis.items():
                    if tf_key.startswith('tf_'):
                        cursor.execute('''
                            INSERT INTO signal_analysis (
                                signal_id, timeframe, trend, rsi, rsi_status,
                                macd_signal, macd_line, macd_histogram,
                                atr, atr_status, atr_multiplier, close_price,
                                analysis_timestamp
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            signal_id,
                            analysis.get('timeframe', 'UNKNOWN'),
                            analysis.get('ema_trend', 'NEUTRO'),
                            analysis.get('rsi'),
                            analysis.get('rsi_status', 'NEUTRO'),
                            analysis.get('macd_signal', 'NEUTRO'),
                            analysis.get('macd_line'),
                            analysis.get('macd_histogram'),
                            analysis.get('atr'),
                            analysis.get('atr_status', 'NORMAL'),
                            analysis.get('atr_multiplier', 1.0),
                            analysis.get('close_price', 0.0),
                            analysis.get('analysis_timestamp')
                        ))
                
                # Guardar divergencias - CORREGIDO
                divergences = analysis_result.get('divergences', [])
                for divergence in divergences:
                    # Manejar tanto objetos Divergence como dicts
                    if hasattr(divergence, 'type'):
                        # Es un objeto Divergence
                        divergence_data = {
                            'type': divergence.type,
                            'indicator': divergence.indicator,
                            'timeframe': divergence.timeframe,
                            'strength': divergence.strength,
                            'confidence': getattr(divergence, 'confidence', 0.5),
                            'price_swing_low': divergence.price_swing_low,
                            'price_swing_high': divergence.price_swing_high,
                            'indicator_swing_low': divergence.indicator_swing_low,
                            'indicator_swing_high': divergence.indicator_swing_high
                        }
                    else:
                        # Es un dict
                        divergence_data = divergence
                    
                    cursor.execute('''
                        INSERT INTO divergences (
                            signal_id, type, indicator, timeframe, strength, confidence,
                            price_swing_low, price_swing_high,
                            indicator_swing_low, indicator_swing_high
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        signal_id,
                        divergence_data.get('type'),
                        divergence_data.get('indicator'),
                        divergence_data.get('timeframe'),
                        divergence_data.get('strength', 'weak'),
                        divergence_data.get('confidence', 0.5),
                        divergence_data.get('price_swing_low'),
                        divergence_data.get('price_swing_high'),
                        divergence_data.get('indicator_swing_low'),
                        divergence_data.get('indicator_swing_high')
                    ))
                
                conn.commit()
                logger.info(f"✅ Señal {signal_id} guardada en base de datos: {signal_data.get('pair')}")
                return signal_id
                
        except Exception as e:
            logger.error(f"❌ Error guardando señal en base de datos: {e}")
            return None
    
    def update_signal_status(self, signal_id: int, status: str, 
                           confirmation_status: str = None) -> bool:
        """Actualiza el estado de una señal - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                update_time = datetime.now().isoformat()
                
                if confirmation_status:
                    cursor.execute('''
                        UPDATE signals 
                        SET status = ?, confirmation_status = ?, updated_at = ?
                        WHERE id = ?
                    ''', (status, confirmation_status, update_time, signal_id))
                else:
                    cursor.execute('''
                        UPDATE signals 
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                    ''', (status, update_time, signal_id))
                
                conn.commit()
                logger.info(f"✅ Señal {signal_id} actualizada a estado: {status}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error actualizando señal {signal_id}: {e}")
            return False
    
    def get_pending_signals(self) -> List[Dict]:
        """Obtiene señales en estado 'waiting' o 'received' - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE status IN ('waiting', 'received', 'monitoring')
                    ORDER BY timestamp DESC
                ''')
                
                signals = [dict(row) for row in cursor.fetchall()]
                
                # Parsear JSON de analysis_summary
                for signal in signals:
                    if signal.get('analysis_summary'):
                        try:
                            signal['analysis_summary'] = json.loads(signal['analysis_summary'])
                        except:
                            signal['analysis_summary'] = {}
                
                logger.debug(f"📊 Obtenidas {len(signals)} señales pendientes")
                return signals
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo señales pendientes: {e}")
            return []
    
    def get_signal_analysis(self, signal_id: int) -> Optional[Dict]:
        """Obtiene el análisis completo de una señal - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Obtener señal principal
                cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
                signal = cursor.fetchone()
                if not signal:
                    logger.warning(f"Señal {signal_id} no encontrada")
                    return None
                
                signal_dict = dict(signal)
                
                # Parsear analysis_summary
                if signal_dict.get('analysis_summary'):
                    try:
                        signal_dict['analysis_summary'] = json.loads(signal_dict['analysis_summary'])
                    except:
                        signal_dict['analysis_summary'] = {}
                
                # Obtener análisis por timeframe
                cursor.execute('''
                    SELECT * FROM signal_analysis 
                    WHERE signal_id = ?
                    ORDER BY timeframe
                ''', (signal_id,))
                analysis = [dict(row) for row in cursor.fetchall()]
                signal_dict['analysis'] = analysis
                
                # Obtener divergencias
                cursor.execute('''
                    SELECT * FROM divergences 
                    WHERE signal_id = ?
                    ORDER BY confidence DESC, strength DESC
                ''', (signal_id,))
                divergences = [dict(row) for row in cursor.fetchall()]
                signal_dict['divergences'] = divergences
                
                return signal_dict
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo análisis de señal {signal_id}: {e}")
            return None
    
    def get_recent_signals(self, hours: int = 24, pair: str = None) -> List[Dict]:
        """Obtiene señales recientes - NUEVO MÉTODO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
                if pair:
                    cursor.execute('''
                        SELECT * FROM signals 
                        WHERE timestamp > ? AND pair = ?
                        ORDER BY timestamp DESC
                    ''', (cutoff_time, pair))
                else:
                    cursor.execute('''
                        SELECT * FROM signals 
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    ''', (cutoff_time,))
                
                signals = [dict(row) for row in cursor.fetchall()]
                
                # Parsear analysis_summary
                for signal in signals:
                    if signal.get('analysis_summary'):
                        try:
                            signal['analysis_summary'] = json.loads(signal['analysis_summary'])
                        except:
                            signal['analysis_summary'] = {}
                
                return signals
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo señales recientes: {e}")
            return []
    
    def get_signals_by_time_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Obtiene señales dentro de un rango de tiempo - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM signals 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                ''', (start_date, end_date))
                
                signals = [dict(row) for row in cursor.fetchall()]
                return signals
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo señales por rango: {e}")
            return []
    
    def get_signal_stats(self, days: int = 7) -> Dict[str, Any]:
        """Obtiene estadísticas de señales - NUEVO MÉTODO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days)
                
                # Total de señales
                cursor.execute('SELECT COUNT(*) FROM signals WHERE timestamp > ?', (cutoff_date,))
                total_signals = cursor.fetchone()[0]
                
                # Señales por estado
                cursor.execute('''
                    SELECT status, COUNT(*) 
                    FROM signals 
                    WHERE timestamp > ? 
                    GROUP BY status
                ''', (cutoff_date,))
                status_counts = dict(cursor.fetchall())
                
                # Señales por par
                cursor.execute('''
                    SELECT pair, COUNT(*) 
                    FROM signals 
                    WHERE timestamp > ? 
                    GROUP BY pair 
                    ORDER BY COUNT(*) DESC
                ''', (cutoff_date,))
                pair_counts = dict(cursor.fetchall())
                
                # Tasa de confirmación
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN confirmation_status IN ('CONFIRMADA', 'PARCIALMENTE CONFIRMADA') THEN 1 ELSE 0 END) as confirmed
                    FROM signals 
                    WHERE timestamp > ?
                ''', (cutoff_date,))
                total, confirmed = cursor.fetchone()
                confirmation_rate = (confirmed / total * 100) if total > 0 else 0
                
                return {
                    'total_signals': total_signals,
                    'status_counts': status_counts,
                    'pair_counts': pair_counts,
                    'confirmation_rate': round(confirmation_rate, 1),
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {}
    
    def cleanup_old_signals(self, days_to_keep: int = 30) -> int:
        """Elimina señales más antiguas que days_to_keep días - MEJORADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calcular fecha límite
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # Contar registros a eliminar
                cursor.execute('SELECT COUNT(*) FROM signals WHERE timestamp < ?', (cutoff_date,))
                total_to_delete = cursor.fetchone()[0]
                
                if total_to_delete == 0:
                    logger.info("✅ No hay señales antiguas para eliminar")
                    return 0
                
                # Eliminar registros relacionados primero (usando CASCADE)
                cursor.execute('DELETE FROM divergences WHERE signal_id IN (SELECT id FROM signals WHERE timestamp < ?)', (cutoff_date,))
                cursor.execute('DELETE FROM signal_analysis WHERE signal_id IN (SELECT id FROM signals WHERE timestamp < ?)', (cutoff_date,))
                
                # Eliminar señales antiguas
                cursor.execute('DELETE FROM signals WHERE timestamp < ?', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"✅ Limpieza BD: {deleted_count} señales eliminadas (>{days_to_keep} días)")
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ Error en limpieza de BD: {e}")
            return 0

# Instancia global
trading_db = TradingDatabase()