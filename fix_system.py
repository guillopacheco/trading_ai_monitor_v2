#!/usr/bin/env python3
"""
Reparación completa del sistema - VERSIÓN CORREGIDA
"""
import asyncio
import logging
from database import trading_db
from bybit_api import bybit_client
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_bybit_connection():
    """Test real de conexión a Bybit"""
    try:
        print("   🔄 Probando conexión real a Bybit...")
        ticker = await bybit_client.get_ticker("BTCUSDT")
        if ticker:
            print("   ✅ Bybit conectado correctamente")
            return True
        else:
            print("   ❌ Bybit no responde")
            return False
    except Exception as e:
        print(f"   ❌ Error conectando a Bybit: {e}")
        return False

async def fix_system_v2():
    """Reparar todos los componentes del sistema - VERSIÓN CORREGIDA"""
    print("🔧 INICIANDO REPARACIÓN DEL SISTEMA V2...")
    
    # 1. Reparar Base de Datos
    print("1. 🔄 Reparando Base de Datos...")
    try:
        trading_db.reconnect()
        if trading_db.is_connected():
            print("   ✅ Base de Datos reparada")
        else:
            print("   ❌ Error reparando Base de Datos")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Reparar Bybit (VERSIÓN CORREGIDA)
    print("2. 🔄 Reparando Bybit...")
    try:
        # Inicializar Bybit
        success = await bybit_client.initialize()
        if success:
            print("   ✅ Bybit inicializado")
            # Test real de conexión
            bybit_connected = await test_bybit_connection()
            if bybit_connected:
                print("   ✅ Bybit completamente operativo")
            else:
                print("   ⚠️ Bybit inicializado pero sin conexión")
        else:
            print("   ❌ Error inicializando Bybit")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Test final
    print("3. 🧪 Test final del sistema...")
    try:
        from command_bot import command_bot
        if not command_bot.is_running:
            await command_bot.start()
        print("   ✅ Bot de comandos activo")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 REPARACIÓN COMPLETADA")
    print("📝 Envía /estado a @gapcbot para verificar")

async def cleanup():
    """Limpieza proper de recursos"""
    try:
        if bybit_client.session:
            await bybit_client.session.close()
    except:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(fix_system_v2())
    except KeyboardInterrupt:
        print("\n🛑 Reparación interrumpida")
    finally:
        asyncio.run(cleanup())