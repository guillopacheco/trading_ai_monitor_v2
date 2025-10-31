#!/usr/bin/env python3
"""
Trading AI Monitor v2 - Sistema Principal - CON HEALTH MONITOR Y OPERATION TRACKER
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

# ✅ NUEVOS IMPORTS
from health_monitor import health_monitor
from operation_tracker import operation_tracker

logger = get_logger(__name__)

# Variable global para acceder a la instancia del monitor desde comandos
monitor_instance = None


class TradingAIMonitor:
    """Clase principal del sistema de trading - CON MONITOREO COMPLETO"""

    def __init__(self):
        self.is_running = False
        self.startup_time = None
        self.last_health_check = None
        self.health_check_interval = 300  # 5 minutos entre verificaciones de salud

    async def startup(self):
        """Inicializa el sistema - CON MONITOREO"""
        try:
            logger.info("🚀 Iniciando Trading AI Monitor v2...")
            self.startup_time = datetime.now()

            # ✅ NUEVO: Registrar inicio en health monitor
            health_monitor.record_telegram_bot_activity()

            # 1. Validar configuración
            validate_config()

            # 2. Testear conexión con Telegram BOT
            logger.info("🤖 Probando conexión con Telegram Bot...")
            if not await telegram_notifier.test_connection():
                logger.warning(
                    "⚠️ No se pudo conectar con Telegram Bot - Comandos desactivados"
                )
                health_monitor.record_connection_issue('telegram', 'No se pudo conectar al bot')
            else:
                logger.info("✅ Conexión con Telegram Bot establecida")
                health_monitor.record_reconnect_attempt('telegram', True)

            # ✅ 3. CONFIGURAR SISTEMA DE COMANDOS CORRECTAMENTE
            await self._setup_telegram_commands()

            # 4. Configurar callback para señales recibidas
            telegram_user_client.set_signal_callback(self.handle_raw_signal_received)

            # 5. Limpieza inicial de BD
            trading_db.cleanup_old_signals(7)

            # ✅ 6. NUEVO: Iniciar detección automática de operaciones
            logger.info("📊 Iniciando detección automática de operaciones...")
            operations_detected = await operation_tracker.auto_detect_operations()
            if operations_detected:
                logger.info("✅ Operaciones detectadas y en seguimiento")
            else:
                logger.info("📭 No hay operaciones abiertas para seguir")

            # 7. Notificar inicio del sistema
            await self.send_startup_notification()

            # ✅ 8. NUEVO: Iniciar verificación periódica de salud
            asyncio.create_task(self._periodic_health_check())

            self.is_running = True
            logger.info("✅ Trading AI Monitor v2 iniciado correctamente")

        except Exception as e:
            logger.error(f"❌ Error en startup: {e}")
            health_monitor.record_error(str(e), "Startup del sistema")
            await telegram_notifier.send_error_notification(
                str(e), "Startup del sistema"
            )
            raise

    async def _setup_telegram_commands(self):
        """Configura el sistema de comandos de Telegram"""
        try:
            logger.info("🔄 Iniciando bot de comandos...")

            # Usar el bot de comandos separado
            from command_bot import command_bot

            await command_bot.start()

            logger.info("✅ Sistema de comandos configurado correctamente")

        except Exception as e:
            logger.error(f"❌ Error configurando comandos de Telegram: {e}")
            health_monitor.record_error(str(e), "Configuración de comandos")
            # No lanzar excepción para que el sistema pueda continuar sin comandos
            logger.warning("⚠️ El sistema continuará sin funcionalidad de comandos")

    async def shutdown(self):
        """Apaga el sistema de manera controlada"""
        try:
            logger.info("🛑 Apagando Trading AI Monitor v2...")
            self.is_running = False

            # ✅ NUEVO: Registrar apagado en health monitor
            health_monitor.record_telegram_bot_activity()  # Última actividad

            # ✅ DETENER BOT DE COMANDOS
            try:
                from command_bot import command_bot

                if command_bot.is_running:
                    await command_bot.stop()
            except Exception as e:
                logger.error(f"❌ Error deteniendo bot de comandos: {e}")

            # Detener componentes existentes
            await telegram_user_client.disconnect()

            # ✅ NUEVO: Detener tracking de operaciones
            operation_tracker.is_tracking = False

            # Enviar notificación de apagado
            uptime = datetime.now() - self.startup_time if self.startup_time else None
            await self.send_shutdown_notification(uptime)

            logger.info("✅ Sistema apagado correctamente")

        except Exception as e:
            logger.error(f"❌ Error en shutdown: {e}")
            health_monitor.record_error(str(e), "Shutdown del sistema")

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

            # ✅ NUEVO: Registrar actividad en health monitor
            health_monitor.record_telegram_bot_activity()

            # Parsear la señal usando helpers.py
            signal_data = parse_signal_message(message_text)

            if not signal_data:
                logger.warning("❌ No se pudo parsear la señal")
                health_monitor.record_error("No se pudo parsear señal", "Parser")
                return

            logger.info(
                f"✅ Señal parseada: {signal_data['pair']} {signal_data['direction']}"
            )

            # ✅ NUEVO: Registrar señal procesada
            health_monitor.record_signal_processed(signal_data)

            # Procesar la señal a través del signal manager
            success = await signal_manager.process_new_signal(signal_data)

            if not success:
                logger.error(f"❌ Error procesando señal: {signal_data['pair']}")
                health_monitor.record_error(f"Error procesando señal {signal_data['pair']}", "Signal Manager")
                await telegram_notifier.send_error_notification(
                    f"Error procesando señal {signal_data['pair']}",
                    "Procesamiento de señal",
                )
            else:
                # ✅ NUEVO: Registrar trade exitoso
                health_monitor.record_successful_trade()

        except Exception as e:
            logger.error(f"❌ Error en callback de señal: {e}")
            health_monitor.record_error(str(e), "Callback de señal")
            await telegram_notifier.send_error_notification(str(e), "Callback de señal")

    async def send_startup_notification(self):
        """Envía notificación de inicio del sistema - CORREGIDO"""
        try:
            # MENSAJE SIMPLIFICADO - Sin caracteres especiales
            message = """
TRADING AI MONITOR V2 - SISTEMA INICIADO

Sistema activo y monitoreando señales
Todos los sistemas operativos correctamente

Comandos disponibles:
/estado - Estado del sistema
/salud - Reporte de salud
/operaciones - Señales recientes

Sistema listo para recibir señales.
"""
            await telegram_notifier.send_alert("Sistema Iniciado", message, "success")
        except Exception as e:
            logger.error(f"Error enviando notificación de inicio: {e}")

    async def send_shutdown_notification(self, uptime: timedelta = None):
        """Envía notificación de apagado del sistema - ACTUALIZADA"""
        try:
            uptime_str = str(uptime).split(".")[0] if uptime else "Desconocido"

            # ✅ NUEVO: Obtener estadísticas finales
            health_report = health_monitor.get_detailed_report()
            operation_stats = operation_tracker.get_operation_stats()

            message = f"""
🛑 **Trading AI Monitor v2 APAGADO** 🛑

**Sistema detenido correctamente**
- 🕒 Tiempo de actividad: {uptime_str}
- 📊 Señales procesadas: {health_report['performance_metrics']['signals_processed']}
- ✅ Trades exitosos: {health_monitor.health_data['successful_trades']}
- 📈 Operaciones activas: {operation_stats['total_open']}
- 💾 Base de datos: Respaldada

**Resumen de Rendimiento:**
- Tasa de éxito: {health_report['performance_metrics']['success_rate']:.1f}%
- Reconexiones exitosas: {health_report['performance_metrics']['reconnect_success_rate']:.1f}%

**Hasta pronto!** 👋
"""
            await telegram_notifier.send_alert("Sistema Apagado", message, "info")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de apagado: {e}")

    def setup_signal_handlers(self):
        """Configura manejadores de señales del sistema"""
        def signal_handler(signum, frame):
            logger.info(f"📞 Señal {signum} recibida, apagando...")
            health_monitor.record_telegram_bot_activity()  # Última actividad registrada
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Bucle principal de ejecución - CON MONITOREO"""
        try:
            global monitor_instance
            monitor_instance = self

            await self.startup()
            self.setup_signal_handlers()

            logger.info("🎧 Iniciando sistemas en paralelo...")
            logger.info("⌨️ Sistema de comandos activo - Envía /estado para verificar")
            logger.info("🩺 Health Monitor activo - Envía /salud para ver estado")
            logger.info("📊 Operation Tracker activo - Envía /operaciones_abiertas")

            # ✅ INICIAR LISTENER EN SEGUNDO PLANO
            asyncio.create_task(self._start_telegram_listener())

            # ✅ MANTENER SISTEMA EJECUTÁNDOSE CON MONITOREO
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Error en bucle principal: {e}")
            health_monitor.record_error(str(e), "Bucle principal")
            await self.shutdown()

    async def _start_telegram_listener(self):
        """Inicia el listener de Telegram en segundo plano"""
        try:
            logger.info("🔍 Iniciando escucha de canal de señales...")
            await telegram_user_client.start_listening()
        except Exception as e:
            logger.error(f"❌ Error en listener de Telegram: {e}")
            health_monitor.record_connection_issue('telegram', f"Listener error: {e}")

    async def _periodic_health_check(self):
        """Verificación periódica del estado del sistema - NUEVO MÉTODO"""
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)

                if not self.is_running:
                    break

                # Verificar salud del sistema
                health_status = health_monitor.check_system_health()

                # Registrar actividad
                health_monitor.record_telegram_bot_activity()

                # Verificar conexión con Telegram Bot periódicamente
                if not await telegram_notifier.test_connection():
                    logger.warning("❌ Problema de conexión con Telegram Bot detectado")
                    health_monitor.record_connection_issue('telegram', 'Conexión perdida en health check')
                else:
                    # Si estaba desconectado y ahora se conectó, registrar reconexión
                    if not health_monitor.connection_status.get('telegram', True):
                        health_monitor.record_reconnect_attempt('telegram', True)

                # Verificar señales pendientes
                pending_count = signal_manager.get_pending_signals_count()
                if pending_count > 0:
                    logger.debug(f"🔍 Monitoreando {pending_count} señales pendientes")

                # Verificar operaciones en seguimiento
                operation_stats = operation_tracker.get_operation_stats()
                if operation_stats['total_open'] > 0:
                    logger.debug(f"📊 Seguimiento activo de {operation_stats['total_open']} operaciones")

                # Alertar si el sistema está degradado
                if health_status['overall_status'] == 'DEGRADED' and len(health_status['alerts']) > 0:
                    logger.warning(f"⚠️ Sistema degradado: {health_status['alerts']}")

            except Exception as e:
                logger.error(f"❌ Error en verificación periódica de salud: {e}")
                health_monitor.record_error(str(e), "Health check periódico")

    async def _system_health_check(self):
        """Verificación del estado del sistema (método legacy - mantener compatibilidad)"""
        try:
            now = datetime.now()
            if (self.last_health_check is None or
                (now - self.last_health_check).total_seconds() >= 1800):

                self.last_health_check = now
                health_monitor.record_telegram_bot_activity()

                if not await telegram_notifier.test_connection():
                    logger.warning("❌ Problema de conexión con Telegram Bot detectado")
                    health_monitor.record_connection_issue('telegram', 'Test conexión falló')

            # Verificar señales pendientes siempre
            pending_count = signal_manager.get_pending_signals_count()
            if pending_count > 0:
                logger.debug(f"🔍 Monitoreando {pending_count} señales pendientes")

        except Exception as e:
            logger.error(f"❌ Error en health check: {e}")
            health_monitor.record_error(str(e), "Health check")


async def main():
    """Función principal - CON MONITOREO"""
    global monitor_instance

    try:
        monitor_instance = TradingAIMonitor()
        await monitor_instance.run()

    except KeyboardInterrupt:
        logger.info("Apagado por usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        # ✅ NUEVO: Registrar error fatal
        health_monitor.record_error(str(e), "Error fatal en main")
        sys.exit(1)
    finally:
        if monitor_instance and monitor_instance.is_running:
            await monitor_instance.shutdown()


if __name__ == "__main__":
    # Configurar logging
    setup_logging()

    # Ejecutar sistema
    asyncio.run(main())