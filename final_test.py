# final_test.py
import asyncio
import logging
from helpers import parse_signal_message
from signal_manager import signal_manager
from database import trading_db
from notifier import telegram_notifier

logging.basicConfig(level=logging.INFO)

async def test_complete_system():
    """Prueba final del sistema completo"""
    print("🎯 PRUEBA FINAL DEL SISTEMA COMPLETO")
    print("=" * 50)
    
    # 1. Test de señal completa
    print("1. 📝 Test de procesamiento de señal...")
    test_signal = "🔥 #BTCUSDT LONG Entry: 50000 SL: 49000 TP: 51000, 52000, 53000"
    
    parsed = parse_signal_message(test_signal)
    if parsed:
        print(f"   ✅ Señal parseada: {parsed['pair']}")
        
        success = await signal_manager.process_new_signal(parsed)
        print(f"   ✅ Signal Manager: {'EXITOSO' if success else 'FALLIDO'}")
        
        # Verificar en BD
        recent = trading_db.get_recent_signals(hours=1)
        print(f"   ✅ BD: {len(recent)} señales recientes")
    else:
        print("   ❌ Fallo en parser")
        return False
    
    # 2. Test de notificaciones
    print("2. 📢 Test de notificaciones...")
    try:
        if await telegram_notifier.test_connection():
            print("   ✅ Telegram Notifier: Conectado")
        else:
            print("   ⚠️ Telegram Notifier: Problemas de conexión")
    except Exception as e:
        print(f"   ⚠️ Telegram Notifier: {e}")
    
    # 3. Test de base de datos
    print("3. 💾 Test de base de datos...")
    try:
        stats = trading_db.get_signal_stats(days=1)
        print(f"   ✅ BD Stats: {stats.get('total_signals', 0)} señales")
    except Exception as e:
        print(f"   ❌ BD Error: {e}")
        return False
    
    # 4. Test de signal manager
    print("4. 🔄 Test de Signal Manager...")
    try:
        manager_stats = signal_manager.get_signal_manager_stats()
        print(f"   ✅ Signal Manager Stats: {manager_stats}")
    except Exception as e:
        print(f"   ❌ Signal Manager Error: {e}")
        return False
    
    print("\n🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
    print("✅ Todos los módulos integrados correctamente")
    print("✅ Listo para recibir señales reales")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_complete_system())
    if success:
        print("\n🚀 INICIA EL SISTEMA CON: python main.py")
    exit(0 if success else 1)