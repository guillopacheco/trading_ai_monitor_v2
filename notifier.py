"""
Sistema de notificaciones por Telegram usando python-telegram-bot - LIMPIADO
"""

import logging
from telegram import Bot
from telegram.error import TelegramError
from typing import Dict, Optional
from config import TELEGRAM_BOT_TOKEN, OUTPUT_CHANNEL_ID
from helpers import format_telegram_message

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Manejador de notificaciones por Telegram - LIMPIADO"""

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

    async def send_signal_analysis(self, analysis_result: Dict) -> bool:
        """
        Envía análisis completo de señal al canal de Telegram
        """
        try:
            if not self.bot:
                logger.error("Bot no inicializado")
                return False

            signal_data = analysis_result.get("signal_original", {})
            summary = analysis_result.get("analysis_summary", {})

            # Usar el formateador mejorado de helpers.py
            message = format_telegram_message(signal_data, summary)

            # Enviar mensaje principal
            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

            logger.info(
                f"✅ Análisis enviado a Telegram: {signal_data.get('pair', 'N/A')}"
            )
            return True

        except TelegramError as e:
            logger.error(f"❌ Error de Telegram enviando análisis: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error enviando análisis a Telegram: {e}")
            return False

    async def send_alert(
        self, title: str, message: str, alert_type: str = "info"
    ) -> bool:
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
                "risk": "🚨",
            }

            emoji = emojis.get(alert_type, "📢")
            formatted_message = f"{emoji} **{title}**\n\n{message}"

            await self.bot.send_message(
                chat_id=self.output_channel_id,
                text=formatted_message,
                parse_mode="Markdown",
            )

            logger.info(f"✅ Alerta enviada: {title}")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando alerta a Telegram: {e}")
            return False

    async def send_confirmation_status(
        self, signal_data: Dict, confirmation_result: Dict
    ) -> bool:
        """
        Envía estado de confirmación de señal
        """
        try:
            if not self.bot:
                return False

            pair = signal_data.get("pair", "N/A")
            direction = signal_data.get("direction", "N/A")
            leverage = signal_data.get("leverage", 20)
            status = confirmation_result.get("status", "N/A")
            confidence = confirmation_result.get("confidence", "N/A")
            match_pct = confirmation_result.get("match_percentage", "N/A")

            status_emoji = (
                "✅" if status == "CONFIRMADA" else "🔄" if "PARCIAL" in status else "⏸️"
            )

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
                parse_mode="Markdown",
            )

            logger.info(
                f"✅ Estado de confirmación enviado: {pair} - {status} (x{leverage})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando estado de confirmación: {e}")
            return False

    async def send_risk_management_info(
        self, signal_data: Dict, position_info: Dict
    ) -> bool:
        """
        Envía información específica de gestión de riesgo
        """
        try:
            if not self.bot:
                return False

            pair = signal_data.get("pair", "N/A")
            leverage = signal_data.get("leverage", 20)

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
                parse_mode="Markdown",
            )

            logger.info(
                f"✅ Info riesgo enviada: {pair} - Riesgo: {position_info.get('real_risk_percent', 'N/A')}%"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando info de riesgo: {e}")
            return False

    async def send_error_notification(
        self, error_message: str, context: str = "Sistema"
    ):
        """Envía notificación de error - CORREGIDO"""
        try:
            message = f"""
    ❌ ERROR DEL SISTEMA ❌

    Contexto: {context}
    Error: {error_message}

    Revisar logs inmediatamente
    """
            # ✅ CORREGIDO: Usar parse_mode=None para evitar problemas de formato
            await self.send_alert(
                "Error del Sistema", message, "error", parse_mode=None
            )

        except Exception as e:
            logger.error(f"❌ Error enviando notificación de error: {e}")

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
