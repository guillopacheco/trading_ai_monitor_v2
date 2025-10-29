#!/usr/bin/env python3
"""
Trading AI Monitor v2 - Sistema Principal - CORREGIDO PARA COMANDOS
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from config import validate_config, SIGNALS_CHANNEL_ID
from logger_config import setup_logging, get_logger
from telegram_client import telegram_user_client
from signal_manager import signal_manager
from notifier import telegram_notifier
from database import trading_db
from helpers import parse_signal_message
from typing import Dict
from datetime import timedelta

logger = get_logger(__name__)

# Variable global para acceder a la instancia del monitor desde comandos
monitor_instance = None


class TradingAIMonitor:
    """Clase principal del sistema de trading - CORREGIDO PARA COMANDOS"""

    def __init__(self):
        self.is_running = False
        self.startup_time = None
        self.last_health_check = None

    async def startup(self):
        """Inicializa el sistema - CORREGIDO"""
        try:
            logger.info("🚀 Iniciando Trading AI Monitor v2...")
            self.startup_time = datetime.now()

            # 1. Validar configuración
            validate_config()

            # 2. Testear conexión con Telegram BOT
            logger.info("🤖 Probando conexión con Telegram Bot...")
            if not await telegram_notifier.test_connection():
                logger.warning("⚠️ No se pudo conectar con Telegram Bot - Comandos desactivados")
            else:
                logger.info("✅ Conexión con Telegram Bot establecida")

            # ✅ 3. CONFIGURAR SISTEMA DE COMANDOS CORRECTAMENTE
            await self._setup_telegram_commands()

            # 4. Configurar callback para señales recibidas
            telegram_user_client.set_signal_callback(self.handle_raw_signal_received)

            # 5. Limpieza inicial de BD
            trading_db.cleanup_old_signals(7)

            # 6. Notificar inicio del sistema
            await self.send_startup_notification()

            self.is_running = True
            logger.info("✅ Trading AI Monitor v2 iniciado correctamente")

        except Exception as e:
            logger.error(f"❌ Error en startup: {e}")
            await telegram_notifier.send_error_notification(
                str(e), "Startup del sistema"
            )
            raise

    async def _setup_telegram_commands(self):
        """Configura el sistema de comandos de Telegram - ✅ CORREGIDO"""
        try:
            logger.info("🔄 Iniciando bot de comandos...")
            
            # Usar el bot de comandos separado
            from command_bot import command_bot
            await command_bot.start()
            
            logger.info("✅ Sistema de comandos configurado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error configurando comandos de Telegram: {e}")
            # No lanzar excepción para que el sistema pueda continuar sin comandos
            logger.warning("⚠️ El sistema continuará sin funcionalidad de comandos")

    async def shutdown(self):
        """Apaga el sistema de manera controlada - CORREGIDO"""
        try:
            logger.info("🛑 Apagando Trading AI Monitor v2...")
            self.is_running = False

            # ✅ DETENER BOT DE COMANDOS
            try:
                from command_bot import command_bot
                if command_bot.is_running:
                    await command_bot.stop()
            except Exception as e:
                logger.error(f"❌ Error deteniendo bot de comandos: {e}")

            # Detener componentes existentes
            await telegram_user_client.disconnect()

            # Enviar notificación de apagado
            uptime = datetime.now() - self.startup_time if self.startup_time else None
            await self.send_shutdown_notification(uptime)

            logger.info("✅ Sistema apagado correctamente")

        except Exception as e:
            logger.error(f"❌ Error en shutdown: {e}")

    async def handle_raw_signal_received(self, raw_signal_data: Dict):
        """
        Callback para procesar señales RAW recibidas de Telegram User Client
        """
        try:
            if not self.is_running:
                logger.warning("Sistema no está ejecutándose, ignorando señal")
                return

            message_text = raw_signal_data.get("message_text", "")
            logger.info(f"📨 Procesando señal recibida: {message_text[:100]}...")

            # Parsear la señal usando helpers.py
            signal_data = parse_signal_message(message_text)

            if not signal_data:
                logger.warning("❌ No se pudo parsear la señal")
                return

            logger.info(
                f"✅ Señal parseada: {signal_data['pair']} {signal_data['direction']}"
            )

            # Procesar la señal a través del signal manager
            success = await signal_manager.process_new_signal(signal_data)

            if not success:
                logger.error(f"❌ Error procesando señal: {signal_data['pair']}")
                await telegram_notifier.send_error_notification(
                    f"Error procesando señal {signal_data['pair']}",
                    "Procesamiento de señal",
                )

        except Exception as e:
            logger.error(f"❌ Error en callback de señal: {e}")
            await telegram_notifier.send_error_notification(str(e), "Callback de señal")

    async def send_startup_notification(self):
        """Envía notificación de inicio del sistema"""
        try:
            message = f"""
🤖 **Trading AI Monitor v2 INICIADO** 🤖

**Sistema activo y monitoreando señales**
- 🕒 Hora de inicio: {self.startup_time.strftime('%Y-%m-%d %H:%M:%S')}
- 📊 Modo: Análisis y Notificaciones
- 🔍 Monitoreo: Canal de señales (User Account)
- 📢 Salida: Canal de resultados (Bot)
- 💾 Base de datos: Operacional
- ⌨️ Comandos: /operaciones, /estado, /revisar, /seguimiento

**Configuración:**
✅ User Account: Conectado para leer señales
✅ Bot: Conectado para enviar resultados  
✅ Parser: Configurado para formato Andy Insider
✅ Análisis: Multi-temporalidad activa
✅ Comandos: Sistema de comandos activado

**Esperando señales del canal...**
"""
            await telegram_notifier.send_alert("Sistema Iniciado", message, "success")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de inicio: {e}")

    async def send_shutdown_notification(self, uptime: timedelta = None):
        """Envía notificación de apagado del sistema"""
        try:
            uptime_str = str(uptime).split(".")[0] if uptime else "Desconocido"

            message = f"""
🛑 **Trading AI Monitor v2 APAGADO** 🛑

**Sistema detenido correctamente**
- 🕒 Tiempo de actividad: {uptime_str}
- 📊 Señales procesadas: {signal_manager.get_pending_signals_count()}
- 💾 Base de datos: Respaldada

**Hasta pronto!** 👋
"""
            await telegram_notifier.send_alert("Sistema Apagado", message, "info")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de apagado: {e}")

    def setup_signal_handlers(self):
        """Configura manejadores de señales del sistema"""

        def signal_handler(signum, frame):
            logger.info(f"📞 Señal {signum} recibida, apagando...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Bucle principal de ejecución - VERSIÓN SIMPLIFICADA"""
        try:
            await self.startup()
            self.setup_signal_handlers()

            logger.info("🎧 Iniciando sistemas en paralelo...")
            logger.info("⌨️ Sistema de comandos activo - Envía /estado para verificar")

            # ✅ INICIAR LISTENER EN SEGUNDO PLANO
            asyncio.create_task(self._start_telegram_listener())

            # ✅ MANTENER SISTEMA EJECUTÁNDOSE PARA COMANDOS
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Error en bucle principal: {e}")
            await self.shutdown()

    async def _start_telegram_listener(self):
        """Inicia el listener de Telegram en segundo plano"""
        try:
            logger.info("🔍 Iniciando escucha de canal de señales...")
            await telegram_user_client.start_listening()
        except Exception as e:
            logger.error(f"❌ Error en listener de Telegram: {e}")

    async def _system_health_check(self):
        """Verificación periódica del estado del sistema"""
        try:
            now = datetime.now()
            if (
                self.last_health_check is None
                or (now - self.last_health_check).total_seconds() >= 1800
            ):

                self.last_health_check = now

                if not await telegram_notifier.test_connection():
                    logger.warning("❌ Problema de conexión con Telegram Bot detectado")

            # Verificar señales pendientes siempre
            pending_count = signal_manager.get_pending_signals_count()
            if pending_count > 0:
                logger.debug(f"🔍 Monitoreando {pending_count} señales pendientes")

        except Exception as e:
            logger.error(f"❌ Error en health check: {e}")


async def main():
    """Función principal"""
    global monitor_instance
    monitor_instance = TradingAIMonitor()

    try:
        await monitor_instance.run()
    except KeyboardInterrupt:
        logger.info("Apagado por usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
    finally:
        if monitor_instance and monitor_instance.is_running:
            await monitor_instance.shutdown()


if __name__ == "__main__":
    # Configurar logging
    setup_logging()

    # Ejecutar sistema
    asyncio.run(main())