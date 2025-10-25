"""
Sistema de notificaciones por Telegram usando python-telegram-bot - ACTUALIZADO CON COMANDOS
"""
import logging
from telegram import Bot, Update
from telegram.ext import CommandHandler, CallbackContext
from telegram.error import TelegramError
from typing import Dict, Optional
from config import TELEGRAM_BOT_TOKEN, OUTPUT_CHANNEL_ID
from helpers import format_telegram_message
from database import trading_db  # ✅ NUEVO IMPORT

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Manejador de notificaciones por Telegram - ACTUALIZADO CON COMANDOS"""
    
    def __init__(self):
        self.bot = None
        self.output_channel_id = OUTPUT_CHANNEL_ID
        self._initialize_bot()
    
    def _initialize_bot(self):
        """Inicializa el bot de Telegram"""
        try:
            if not TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN no configurado")
            
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            logger.info("✅ Bot de notificaciones inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando bot: {e}")
            self.bot = None
    
    async def setup_commands(self, application):
        """Configura los handlers de comandos - ✅ NUEVA FUNCIÓN"""
        try:
            # Handler para /operaciones
            application.add_handler(CommandHandler("operaciones", self.handle_operaciones_command))
            # Handler para /estado
            application.add_handler(CommandHandler("estado", self.handle_estado_command))
            # Handler para /revisar
            application.add_handler(CommandHandler("revisar", self.handle_revisar_command))
            # Handler para /seguimiento
            application.add_handler(CommandHandler("seguimiento", self.handle_seguimiento_command))
            logger.info("✅ Comandos de Telegram configurados")
        except Exception as e:
            logger.error(f"❌ Error configurando comandos: {e}")
    
    async def handle_operaciones_command(self, update: Update, context: CallbackContext):
        """Maneja el comando /operaciones - ✅ NUEVA FUNCIÓN"""
        try:
            # Obtener señales recientes (últimas 24 horas)
            recent_signals = trading_db.get_recent_signals(hours=24)
            
            if not recent_signals:
                await update.message.reply_text(
                    "📊 **No hay operaciones recientes** (últimas 24 horas)\n\n"
                    "Esperando nuevas señales... 📡",
                    parse_mode='Markdown'
                )
                return
            
            # Agrupar por estado
            confirmed_signals = [s for s in recent_signals if s.get('confirmation_status') in ['CONFIRMADA', 'PARCIALMENTE CONFIRMADA']]
            pending_signals = [s for s in recent_signals if s.get('status') in ['waiting', 'received', 'monitoring']]
            other_signals = [s for s in recent_signals if s not in confirmed_signals + pending_signals]
            
            message = "📊 **OPERACIONES RECIENTES** (24h)\n\n"
            
            # Señales confirmadas
            if confirmed_signals:
                message += "✅ **SEÑALES CONFIRMADAS:**\n"
                for signal in confirmed_signals[:5]:  # Máximo 5
                    leverage = signal.get('leverage', 20)
                    entry = signal.get('entry_price', 'N/A')
                    direction_emoji = "📉" if signal['direction'] == "SHORT" else "📈"
                    message += f"• {direction_emoji} {signal['pair']} {signal['direction']} (x{leverage})\n"
                    message += f"  Entry: {entry} | {signal['confirmation_status']}\n"
                message += "\n"
            
            # Señales pendientes
            if pending_signals:
                message += "⏳ **SEÑALES PENDIENTES:**\n"
                for signal in pending_signals[:5]:  # Máximo 5
                    leverage = signal.get('leverage', 20)
                    entry = signal.get('entry_price', 'N/A')
                    direction_emoji = "📉" if signal['direction'] == "SHORT" else "📈"
                    message += f"• {direction_emoji} {signal['pair']} {signal['direction']} (x{leverage})\n"
                    message += f"  Entry: {entry} | {signal['status']}\n"
                message += "\n"
            
            # Otras señales
            if other_signals:
                message += "📈 **OTRAS SEÑALES:**\n"
                for signal in other_signals[:3]:  # Máximo 3
                    leverage = signal.get('leverage', 20)
                    direction_emoji = "📉" if signal['direction'] == "SHORT" else "📈"
                    message += f"• {direction_emoji} {signal['pair']} {signal['direction']} (x{leverage}) - {signal.get('status', 'N/A')}\n"
                message += "\n"
            
            # Resumen
            total_signals = len(recent_signals)
            confirmed_count = len(confirmed_signals)
            pending_count = len(pending_signals)
            
            message += f"**📈 RESUMEN:** {total_signals} señales total\n"
            message += f"✅ {confirmed_count} confirmadas | ⏳ {pending_count} pendientes"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"✅ Comando /operaciones ejecutado - {total_signals} señales mostradas")
            
        except Exception as e:
            error_msg = f"❌ Error ejecutando /operaciones: {e}"
            logger.error(error_msg)
            await update.message.reply_text("❌ Error al obtener operaciones. Revisa logs.")
    
    async def handle_estado_command(self, update: Update, context: CallbackContext):
        """Maneja el comando /estado - ✅ NUEVA FUNCIÓN"""
        try:
            from signal_manager import signal_manager  # Import aquí para evitar circular imports
            
            # Obtener estadísticas
            stats = trading_db.get_signal_stats(days=1)  # Últimas 24 horas
            
            message = "🤖 **ESTADO DEL SISTEMA**\n\n"
            message += f"📊 **Señales (24h):** {stats.get('total_signals', 0)}\n"
            message += f"✅ **Tasa confirmación:** {stats.get('confirmation_rate', 0)}%\n"
            message += f"🔄 **Señales pendientes:** {signal_manager.get_pending_signals_count()}\n"
            
            # Pares más activos
            pair_counts = stats.get('pair_counts', {})
            if pair_counts:
                top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                message += f"🔥 **Pares activos:** {', '.join([f'{pair}({count})' for pair, count in top_pairs])}\n"
            
            # Estado de conexión
            message += "\n**🔗 CONEXIONES:**\n"
            message += "• Telegram User: ✅ Conectado\n"
            message += "• Telegram Bot: ✅ Conectado\n"
            message += "• Bybit API: ✅ Operativa\n"
            message += "• Base de datos: ✅ Operativa\n"
            
            message += "\n**📋 COMANDOS DISPONIBLES:**\n"
            message += "• `/operaciones` - Ver señales recientes\n"
            message += "• `/estado` - Estado del sistema\n"
            message += "• `/revisar` - Revisar operaciones abiertas\n"
            message += "• `/seguimiento` - Ver seguimiento actual\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info("✅ Comando /estado ejecutado")
            
        except Exception as e:
            error_msg = f"❌ Error ejecutando /estado: {e}"
            logger.error(error_msg)
            await update.message.reply_text("❌ Error al obtener estado. Revisa logs.")

    async def handle_revisar_command(self, update: Update, context: CallbackContext):
        """Maneja el comando /revisar - Revisa y inicia seguimiento automático"""
        try:
            from operation_tracker import operation_tracker
            
            await update.message.reply_text("🔍 Buscando operaciones abiertas en Bybit...")
            
            # Detectar operaciones automáticamente
            operations_found = await operation_tracker.auto_detect_operations()
            
            if operations_found:
                open_operations = operation_tracker.get_open_operations()
                
                message = "✅ **SEGUIMIENTO INICIADO**\n\n"
                message += f"📊 **{len(open_operations)} operaciones detectadas:**\n\n"
                
                for op in open_operations:
                    signal = op['signal_data']
                    current_roi = op.get('current_roi', 0)
                    
                    direction_emoji = "📈" if signal['direction'] == "LONG" else "📉"
                    message += f"{direction_emoji} **{signal['pair']}** {signal['direction']} (x{signal.get('leverage', 20)})\n"
                    message += f"   Entry: {op['actual_entry']} | Size: {op.get('size', 'N/A')}\n"
                    message += f"   ROI actual: {current_roi}%\n\n"
                
                message += "🤖 **El sistema monitoreará automáticamente:**\n"
                message += "• Precios en tiempo real\n"
                message += "• Take Profits alcanzados\n" 
                message += "• ROI -30% para reversión/cierre\n"
                message += "• Alertas de recomendaciones\n\n"
                message += "📝 Usa /seguimiento para ver estado actual"
                
            else:
                message = "📭 **No hay operaciones abiertas**\n\n"
                message += "No se detectaron posiciones activas en Bybit.\n\n"
                message += "**Cuando abras una operación:**\n"
                message += "1. Ejecuta /revisar nuevamente\n"
                message += "2. El sistema la detectará automáticamente\n"
                message += "3. Comenzará el monitoreo en tiempo real"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en /revisar: {e}")
            await update.message.reply_text("❌ Error revisando operaciones")

    async def handle_seguimiento_command(self, update: Update, context: CallbackContext):
        """Maneja el comando /seguimiento - Estado actual del seguimiento"""
        try:
            from operation_tracker import operation_tracker
            
            open_operations = operation_tracker.get_open_operations()
            
            if not open_operations:
                await update.message.reply_text(
                    "📭 **No hay operaciones en seguimiento**\n\n"
                    "Usa /revisar para detectar operaciones abiertas en Bybit",
                    parse_mode='Markdown'
                )
                return
            
            message = "📊 **OPERACIONES EN SEGUIMIENTO**\n\n"
            
            for op in open_operations:
                signal = op['signal_data']
                current_roi = op.get('current_roi', 0)
                max_roi = op.get('max_roi', 0)
                current_price = op.get('current_price', 'N/A')
                
                direction_emoji = "📈" if signal['direction'] == "LONG" else "📉"
                roi_color = "🟢" if current_roi > 0 else "🔴" if current_roi < 0 else "⚪"
                
                message += f"{direction_emoji} **{signal['pair']}** {signal['direction']} (x{signal.get('leverage', 20)})\n"
                message += f"   Entry: {op['actual_entry']} | Actual: {current_price}\n"
                message += f"   {roi_color} ROI: {current_roi}% | Máx: {max_roi}%\n"
                
                # Última recomendación
                if op['recommendation_history']:
                    last_rec = op['recommendation_history'][-1]
                    rec_emoji = {
                        "MANTENER": "🟡",
                        "CERRAR_PARCIAL": "🟠", 
                        "CERRAR_TOTAL": "🔴",
                        "REVERTIR": "🔄"
                    }.get(last_rec['recommendation'], "⚪")
                    
                    message += f"   {rec_emoji} Recomendación: {last_rec['recommendation']}\n"
                    message += f"   📝 {last_rec['reason'][:50]}...\n"
                
                message += "\n"
            
            stats = operation_tracker.get_operation_stats()
            message += f"**📈 RESUMEN:** {stats['total_open']} operaciones | ROI Prom: {stats['average_roi']:.1f}%"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Error en /seguimiento: {e}")
            await update.message.reply_text("❌ Error obteniendo seguimiento")
    
    async def send_signal_analysis(self, analysis_result: Dict) -> bool:
        """
        Envía análisis completo de señal al canal de Telegram - ACTUALIZADO
        """
        try:
            if not self.bot:
                logger.error("Bot no inicializado")
                return False
            
            signal_data = analysis_result.get('signal_original', {})
            summary = analysis_result.get('analysis_summary', {})
            
            # Usar el formateador mejorado de helpers.py
            message = format_telegram_message(signal_data, summary)
            
            # Enviar mensaje principal
            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Enviar alerta de divergencia si existe
            if summary.get('divergence_detected') == 'Sí':
                divergence_msg = f"⚠️ **ALERTA DIVERGENCIA** ⚠️\n\n"
                divergence_msg += f"**{signal_data.get('pair', 'N/A')}** - {summary.get('divergence_type', 'N/A')}\n"
                divergence_msg += f"Posible reversión de tendencia detectada"
                
                await self.bot.send_message(
                    chat_id=self.output_channel_id,
                    text=divergence_msg,
                    parse_mode='Markdown'
                )
            
            # Enviar alerta de riesgo si es muy alto
            real_risk = summary.get('real_risk_percent', 0)
            if real_risk > 5:  # Más del 5% de riesgo real
                risk_msg = f"🚨 **ALTO RIESGO DETECTADO** 🚨\n\n"
                risk_msg += f"**{signal_data.get('pair', 'N/A')}** - Riesgo real: {real_risk}%\n"
                risk_msg += f"Considerar reducir tamaño de posición"
                
                await self.bot.send_message(
                    chat_id=self.output_channel_id,
                    text=risk_msg,
                    parse_mode='Markdown'
                )
            
            logger.info(f"✅ Análisis enviado a Telegram: {signal_data.get('pair', 'N/A')} (x{signal_data.get('leverage', 20)})")
            return True
            
        except TelegramError as e:
            logger.error(f"❌ Error de Telegram enviando análisis: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error enviando análisis a Telegram: {e}")
            return False
    
    async def send_alert(self, title: str, message: str, alert_type: str = "info") -> bool:
        """
        Envía alerta genérica al canal
        """
        try:
            if not self.bot:
                logger.error("Bot no inicializado")
                return False
            
            # Emojis según tipo de alerta
            emojis = {
                "info": "ℹ️",
                "warning": "⚠️", 
                "error": "❌",
                "success": "✅",
                "risk": "🚨"
            }
            
            emoji = emojis.get(alert_type, "📢")
            formatted_message = f"{emoji} **{title}**\n\n{message}"
            
            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Alerta enviada: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta a Telegram: {e}")
            return False
    
    async def send_confirmation_status(self, signal_data: Dict, confirmation_result: Dict) -> bool:
        """
        Envía estado de confirmación de señal - ACTUALIZADO CON APALANCAMIENTO
        """
        try:
            if not self.bot:
                return False
            
            pair = signal_data.get('pair', 'N/A')
            direction = signal_data.get('direction', 'N/A')
            leverage = signal_data.get('leverage', 20)
            status = confirmation_result.get('status', 'N/A')
            confidence = confirmation_result.get('confidence', 'N/A')
            match_pct = confirmation_result.get('match_percentage', 'N/A')
            
            status_emoji = "✅" if status == "CONFIRMADA" else "🔄" if "PARCIAL" in status else "⏸️"
            
            message = f"""
{status_emoji} **Estado de Confirmación - {pair}** 

**Señal:** {direction} (x{leverage})
**Estado:** {status}
**Confianza:** {confidence}
**Coincidencia:** {match_pct}%

**Acción Recomendada:** {'ENTRAR' if status == 'CONFIRMADA' else 'ESPERAR CONFIRMACIÓN'}
"""
            
            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=message.strip(),
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Estado de confirmación enviado: {pair} - {status} (x{leverage})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando estado de confirmación: {e}")
            return False
    
    async def send_risk_management_info(self, signal_data: Dict, position_info: Dict) -> bool:
        """
        Envía información específica de gestión de riesgo - NUEVA FUNCIÓN
        """
        try:
            if not self.bot:
                return False
            
            pair = signal_data.get('pair', 'N/A')
            leverage = signal_data.get('leverage', 20)
            
            message = f"""
💰 **GESTIÓN DE RIESGO - {pair}**

**Configuración:**
- Apalancamiento: x{leverage}
- Tamaño Posición: {position_info.get('position_size', 'N/A')} USDT
- Riesgo/Operación: {position_info.get('dollar_risk', 'N/A')} USDT
- Riesgo Real: {position_info.get('real_risk_percent', 'N/A')}%

**Límites:**
- Posición Máxima: {position_info.get('max_position_allowed', 'N/A')} USDT
- Ratio R/R: {position_info.get('risk_reward_ratio', 'N/A')}

**Recomendación:** {'✅ POSICIÓN SEGURA' if position_info.get('real_risk_percent', 0) <= 5 else '⚠️ CONSIDERAR REDUCIR POSICIÓN'}
"""
            
            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=message.strip(),
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Info riesgo enviada: {pair} - Riesgo: {position_info.get('real_risk_percent', 'N/A')}%")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando info de riesgo: {e}")
            return False
    
    async def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """
        Envía notificación de error al canal
        """
        try:
            if not self.bot:
                return False
            
            message = f"""
❌ **ERROR DEL SISTEMA** ❌

**Contexto:** {context}
**Error:** {error_message}

**Revisar logs inmediatamente**
"""
            
            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=message.strip(),
                parse_mode='Markdown'
            )
            
            logger.error(f"✅ Notificación de error enviada: {context}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """
        Testea la conexión con Telegram
        """
        try:
            if not self.bot:
                return False
            
            await self.bot.get_me()
            logger.info("✅ Conexión con Telegram establecida")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando con Telegram: {e}")
            return False

# Instancia global
telegram_notifier = TelegramNotifier()