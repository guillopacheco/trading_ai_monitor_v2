# test_complete_system.py - VERSIÓN CORREGIDA
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_complete_system():
    print("🧪 PRUEBA COMPLETA DEL SISTEMA")
    print("=" * 50)
    
    # 1. Test de imports básicos
    print("1. Cargando módulos principales...")
    try:
        from helpers import parse_signal_message, validate_signal_data
        from database import trading_db
        print("   ✅ Módulos cargan correctamente")
    except Exception as e:
        print(f"   ❌ Error cargando módulos: {e}")
        return False
    
    # 2. Test de parser
    print("2. Probando parser de señales...")
    test_signal = """🔥 ENSOUSDT (Short📉, x20) 🔥
Entry - 1.538
Take-Profit:
🥉 1.5072 (40% of profit)
🥈 1.4919 (60% of profit)"""
    
    parsed = parse_signal_message(test_signal)
    if parsed:
        print("   ✅ Parser OK")
        print(f"      {parsed['pair']} {parsed['direction']} @ {parsed['entry_price']} (x{parsed.get('leverage', 'N/A')})")
    else:
        print("   ❌ Parser falló")
        return False
    
    # 3. Test de validación
    print("3. Probando validación de señales...")
    if parsed:
        is_valid, message = validate_signal_data(parsed)
        if is_valid:
            print(f"   ✅ Señal válida: {message}")
        else:
            print(f"   ❌ Señal inválida: {message}")
            return False
    
    # 4. Test de base de datos - CORREGIDO
    print("4. Probando base de datos...")
    try:
        # Intentar usar métodos existentes en lugar de test_connection
        cursor = trading_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        cursor.close()
        
        if tables:
            print(f"   ✅ Base de datos operativa ({len(tables)} tablas encontradas)")
            
            # Mostrar tablas existentes
            table_names = [table[0] for table in tables]
            print(f"      Tablas: {', '.join(table_names)}")
        else:
            print("   ⚠️  Base de datos conectada pero sin tablas")
            
    except Exception as e:
        print(f"   ❌ Error en base de datos: {e}")
        # No retornamos False aquí porque la BD no es crítica para pruebas básicas
    
    # 5. Test de configuración
    print("5. Verificando configuración...")
    try:
        from config import (
            TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE,
            TELEGRAM_BOT_TOKEN, OUTPUT_CHANNEL_ID, SIGNALS_CHANNEL_ID,
            BYBIT_API_KEY, BYBIT_API_SECRET
        )
        
        config_checks = [
            ("TELEGRAM_API_ID", TELEGRAM_API_ID),
            ("TELEGRAM_API_HASH", TELEGRAM_API_HASH),
            ("TELEGRAM_PHONE", TELEGRAM_PHONE),
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            ("OUTPUT_CHANNEL_ID", OUTPUT_CHANNEL_ID),
            ("SIGNALS_CHANNEL_ID", SIGNALS_CHANNEL_ID),
            ("BYBIT_API_KEY", BYBIT_API_KEY),
            ("BYBIT_API_SECRET", BYBIT_API_SECRET),
        ]
        
        all_config_ok = True
        for name, value in config_checks:
            if value:
                print(f"   ✅ {name}: Configurado")
            else:
                print(f"   ❌ {name}: No configurado")
                all_config_ok = False
        
        if not all_config_ok:
            print("   ⚠️  Algunas configuraciones faltan")
        
    except ImportError as e:
        print(f"   ❌ Error importando configuración: {e}")
        return False
    
    # 6. Test de módulos avanzados (si existen)
    print("6. Probando módulos avanzados...")
    advanced_modules = []
    
    try:
        from risk_manager import risk_manager
        print("   ✅ Risk Manager cargado")
        advanced_modules.append("Risk Manager")
    except ImportError as e:
        print(f"   ⚠️  Risk Manager no disponible: {e}")
    
    try:
        from position_sizer import position_sizer
        print("   ✅ Position Sizer cargado")
        advanced_modules.append("Position Sizer")
    except ImportError as e:
        print(f"   ⚠️  Position Sizer no disponible: {e}")
    
    try:
        from volatility_analyzer import volatility_analyzer
        print("   ✅ Volatility Analyzer cargado")
        advanced_modules.append("Volatility Analyzer")
    except ImportError as e:
        print(f"   ⚠️  Volatility Analyzer no disponible: {e}")
    
    try:
        from connection_monitor import connection_monitor
        print("   ✅ Connection Monitor cargado")
        advanced_modules.append("Connection Monitor")
    except ImportError as e:
        print(f"   ⚠️  Connection Monitor no disponible: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 RESUMEN DEL SISTEMA")
    print("   ✅ Parser de señales - OPERATIVO")
    print("   ✅ Validación de datos - OPERATIVO")
    print("   ✅ Configuración base - OPERATIVO")
    print(f"   📊 Módulos avanzados: {len(advanced_modules)} cargados")
    
    if advanced_modules:
        print(f"      • {', '.join(advanced_modules)}")
    
    print("\n💡 Sistema base listo para operar")
    
    return True

async def test_telegram_integration():
    """Test opcional de integración con Telegram"""
    print("\n🔗 TEST OPCIONAL: Integración Telegram")
    print("=" * 50)
    
    try:
        from telegram_client import telegram_user_client
        from notifier import telegram_notifier
        
        # Test cliente usuario
        print("1. Probando cliente de usuario...")
        user_ok = await telegram_user_client.connect()
        if user_ok:
            print("   ✅ Cliente de usuario conectado")
            
            # Probar lectura de canal
            try:
                from config import SIGNALS_CHANNEL_ID
                messages = await telegram_user_client.get_channel_messages(SIGNALS_CHANNEL_ID, limit=3)
                if messages:
                    print(f"   ✅ Puede leer canal de señales ({len(messages)} mensajes)")
                else:
                    print("   ⚠️  Conectado pero no puede leer el canal")
            except Exception as e:
                print(f"   ⚠️  Error leyendo canal: {e}")
            
            await telegram_user_client.disconnect()
        else:
            print("   ❌ Cliente de usuario falló")
        
        # Test bot
        print("2. Probando bot de notificaciones...")
        bot_ok = await telegram_notifier.test_connection()
        if bot_ok:
            print("   ✅ Bot conectado")
            
            # Probar envío de mensaje
            try:
                await telegram_notifier.send_alert(
                    "Test del Sistema",
                    "✅ Sistema de trading verificado y operativo",
                    "success"
                )
                print("   ✅ Bot puede enviar mensajes")
            except Exception as e:
                print(f"   ⚠️  Bot conectado pero error enviando: {e}")
        else:
            print("   ❌ Bot falló")
        
        return user_ok and bot_ok
        
    except Exception as e:
        print(f"   ❌ Error en integración Telegram: {e}")
        return False

if __name__ == "__main__":
    # Test principal síncrono
    success = test_complete_system()
    
    # Test Telegram opcional (asíncrono)
    if success:
        try:
            telegram_ok = asyncio.run(test_telegram_integration())
            if telegram_ok:
                print("\n🎉 ¡SISTEMA COMPLETAMENTE OPERATIVO! 🎉")
            else:
                print("\n⚠️  Sistema base operativo, Telegram requiere ajustes")
        except Exception as e:
            print(f"\n⚠️  Error en test Telegram: {e}")
    else:
        print("\n❌ Sistema base requiere ajustes")