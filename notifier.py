"""
Sistema de notificaciones mejorado - CON NUEVAS ALERTAS
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Manejador de notificaciones por Telegram - MEJORADO"""
    
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.user_id = TELEGRAM_USER_ID
        self.connected = False

    async def test_connection(self) -> bool:
        """Verifica la conexión con Telegram"""
        try:
            await self.bot.get_me()
            self.connected = True
            logger.info("✅ Conexión con Telegram establecida")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando con Telegram: {e}")
            self.connected = False
            return False

    async def send_alert(self, title: str, message: str, alert_type: str = "info"):
        """Envía alerta a Telegram - MEJORADO"""
        try:
            if not self.connected:
                if not await self.test_connection():
                    return False

            # Emojis según tipo de alerta
            emojis = {
                "success": "✅",
                "error": "❌", 
                "warning": "⚠️",
                "info": "ℹ️"
            }
            emoji = emojis.get(alert_type, "📢")

            formatted_message = f"{emoji} *{title}*\n\n{message}"
            
            await self.bot.send_message(
                chat_id=self.user_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Alerta enviada: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta: {e}")
            return False

    async def send_error_notification(self, error_message: str, context: str = ""):
        """Envía notificación de error"""
        message = f"*Contexto:* {context}\n*Error:* {error_message}"
        return await self.send_alert("Error del Sistema", message, "error")

    async def send_signal_analysis(self, analysis_result: Dict):
        """Envía análisis completo de señal"""
        try:
            summary = analysis_result.get('analysis_summary', {})
            symbol = analysis_result.get('symbol', 'UNKNOWN')
            
            message = f"""
📊 *ANÁLISIS COMPLETO - {symbol}*

*Recomendación:* {summary.get('action', 'N/A')}
*Confianza:* {summary.get('confidence', 'N/A')}
*Match:* {summary.get('match_percentage', 0):.1f}%

*Detalles Técnicos:*
• Tendencia: {summary.get('predominant_trend', 'N/A')}
• RSI Promedio: {summary.get('avg_rsi', 'N/A')}
• Estado: {summary.get('confirmation_status', 'N/A')}

*Razón:* {summary.get('reason', 'Análisis completado')}
"""
            return await self.send_alert(f"Análisis: {symbol}", message, "info")
            
        except Exception as e:
            logger.error(f"❌ Error enviando análisis de señal: {e}")
            return False

    async def send_confirmation_status(self, signal_data: Dict, confirmation_result: Dict):
        """Envía estado de confirmación de señal"""
        try:
            symbol = signal_data.get('pair', 'UNKNOWN')
            status = confirmation_result.get('status', 'PENDIENTE')
            confidence = confirmation_result.get('confidence', 'BAJA')
            
            message = f"""
🎯 *CONFIRMACIÓN DE SEÑAL - {symbol}*

*Estado:* {status}
*Confianza:* {confidence}
*Match:* {confirmation_result.get('match_percentage', 0):.1f}%

*Entry:* {signal_data.get('entry', 'N/A')}
*Dirección:* {signal_data.get('direction', 'N/A')}
*Apalancamiento:* x{signal_data.get('leverage', 1)}
"""
            alert_type = "success" if status == "CONFIRMADA" else "warning"
            return await self.send_alert(f"Confirmación: {symbol}", message, alert_type)
            
        except Exception as e:
            logger.error(f"❌ Error enviando confirmación: {e}")
            return False

    # === NUEVOS MÉTODOS MEJORADOS ===

    async def send_divergence_alert(self, symbol: str, divergence_type: str, strength: str, timeframe: str, confidence: float):
        """Envía alerta de divergencia relevante - NUEVO MÉTODO"""
        try:
            emoji = "🔺" if divergence_type == "bullish" else "🔻"
            strength_emoji = "🟢" if strength == "weak" else "🟡" if strength == "moderate" else "🔴"
            
            message = f"""
{emoji} **DIVERGENCIA DETECTADA** - {symbol}

• Tipo: {divergence_type.upper()}
• Fuerza: {strength.upper()} {strength_emoji}
• Timeframe: {timeframe}
• Confianza: {confidence:.1%}

⚠️ Posible reversión de tendencia
"""
            
            await self.send_alert(
                f"Divergencia {divergence_type} - {symbol}",
                message,
                "warning"
            )
            logger.info(f"📢 Alerta de divergencia enviada: {symbol} {divergence_type}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta de divergencia: {e}")

    async def send_simulation_status(self, active: bool):
        """Envía estado del modo simulación - NUEVO MÉTODO"""
        try:
            if active:
                message = """
🧪 **MODO SIMULACIÓN ACTIVADO**

• Análisis de señales en tiempo real
• Sin ejecución de operaciones
• Base de datos: Actualizada
• Health Monitor: Activo

📊 Todas las funcionalidades operativas excepto ejecución real.
"""
                await self.send_alert("Modo Simulación", message, "info")
            else:
                message = """
⚡ **MODO REAL ACTIVADO**

• Operaciones automáticas: ACTIVADAS
• Ejecución en Bybit: HABILITADA
• Gestión de riesgo: OPERATIVA
• Stop Loss/Take Profit: AUTOMÁTICOS

🚨 El sistema ejecutará operaciones reales.
"""
                await self.send_alert("Modo Real", message, "success")
                
        except Exception as e:
            logger.error(f"❌ Error enviando estado de simulación: {e}")

    async def send_loss_alert(self, symbol: str, loss_percentage: float, current_price: float, entry_price: float, recommendation: str):
        """Envía alerta de pérdida progresiva - NUEVO MÉTODO"""
        try:
            if loss_percentage >= 90:
                emoji = "💀"
                level = "CRÍTICA"
                alert_type = "error"
            elif loss_percentage >= 70:
                emoji = "🚨"
                level = "ALTA"
                alert_type = "error"
            elif loss_percentage >= 50:
                emoji = "⚠️"
                level = "MEDIA"
                alert_type = "warning"
            elif loss_percentage >= 30:
                emoji = "📉"
                level = "MODERADA"
                alert_type = "info"
            else:
                return  # No alertar por pérdidas menores al 30%

            message = f"""
{emoji} **PÉRDIDA {level}** - {symbol}

• Pérdida Actual: {loss_percentage:.1f}%
• Precio Entry: {entry_price:.4f}
• Precio Actual: {current_price:.4f}
• Recomendación: {recommendation}

📊 Monitoreo activo de tendencia.
"""
            
            await self.send_alert(
                f"Pérdida {level} - {symbol}",
                message,
                alert_type
            )
            logger.info(f"📢 Alerta de pérdida enviada: {symbol} {loss_percentage:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta de pérdida: {e}")

    async def send_db_update_notification(self, signal_id: str, symbol: str, action: str, result: str = ""):
        """Envía notificación de actualización en BD - NUEVO MÉTODO"""
        try:
            actions = {
                "closed": "🔄 OPERACIÓN CERRADA",
                "updated": "📝 ACTUALIZACIÓN",
                "created": "📨 NUEVA SEÑAL",
                "rejected": "❌ SEÑAL RECHAZADA"
            }
            
            action_display = actions.get(action, action.upper())
            
            message = f"""
{action_display} - {symbol}

• ID: {signal_id}
• Acción: {action}
• Resultado: {result}
• Hora: {datetime.now().strftime('%H:%M:%S')}

💾 Base de datos actualizada correctamente.
"""
            
            await self.send_alert(
                f"BD: {action_display}",
                message,
                "info" if action in ["updated", "created"] else "success" if action == "closed" else "error"
            )
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación BD: {e}")

    async def send_manual_evaluation(self, symbol: str, analysis_data: Dict):
        """Envía evaluación manual bajo demanda - NUEVO MÉTODO"""
        try:
            current_price = analysis_data.get('current_price', 0)
            trend = analysis_data.get('trend', 'NEUTRO')
            rsi = analysis_data.get('rsi', 50)
            recommendation = analysis_data.get('recommendation', 'MANTENER')
            
            message = f"""
📊 **EVALUACIÓN MANUAL** - {symbol}

• Precio Actual: {current_price:.4f}
• Tendencia: {trend}
• RSI: {rsi:.1f}
• Recomendación: {recommendation}

• EMA Trend: {analysis_data.get('ema_trend', 'N/A')}
• MACD Signal: {analysis_data.get('macd_signal', 'N/A')}
• Volatilidad: {analysis_data.get('volatility', 'N/A')}
"""
            
            await self.send_alert(
                f"Evaluación: {symbol}",
                message,
                "info"
            )
            
        except Exception as e:
            logger.error(f"❌ Error enviando evaluación manual: {e}")

# Instancia global
telegram_notifier = TelegramNotifier()