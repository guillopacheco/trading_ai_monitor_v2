# test_signal_direct.py
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_signal_processing():
    """Prueba el procesamiento de señales directamente"""
    print("🎯 PRUEBA DIRECTA DE PROCESAMIENTO DE SEÑALES")
    print("=" * 60)
    
    try:
        # Importar componentes
        from signal_manager import signal_manager
        from helpers import parse_signal_message
        
        # Señal de prueba
        test_signal = """
🔥 **#TESTUSDT** (Long📈, x10) 🔥

**Entry** - 100.50
**Stop-Loss** - 98.25
**Take-Profit:** 102.75, 105.00, 107.25
"""
        
        print("1. 📝 Parseando señal...")
        parsed_signal = parse_signal_message(test_signal)
        
        if parsed_signal:
            print(f"   ✅ Parseada: {parsed_signal['pair']} {parsed_signal['direction']} @ {parsed_signal['entry']}")
            
            print("2. 🔍 Procesando con Signal Manager...")
            
            # Verificar que signal_manager tenga los métodos necesarios
            if hasattr(signal_manager, 'process_new_signal'):
                success = await signal_manager.process_new_signal(parsed_signal)
                
                if success:
                    print("   ✅ Señal procesada exitosamente")
                    print("   📊 Estadísticas:")
                    print(f"      - Señales procesadas: {getattr(signal_manager, 'signals_processed', 'N/A')}")
                    print(f"      - Señales pendientes: {signal_manager.get_pending_signals_count()}")
                else:
                    print("   ❌ Error procesando señal")
            else:
                print("   ❌ Signal Manager no tiene process_new_signal")
        else:
            print("   ❌ No se pudo parsear la señal")
            
    except Exception as e:
        print(f"   ❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()

async def test_database_save():
    """Prueba guardar señal en base de datos"""
    print("\n3. 💾 Probando guardado en base de datos...")
    
    try:
        from database import trading_db
        from helpers import parse_signal_message
        
        test_signal = "🔥 **#DBTEST** (Short📉, x5) 🔥\n**Entry** - 50.25"
        parsed = parse_signal_message(test_signal)
        
        if parsed:
            # Guardar directamente en BD
            signal_id = trading_db.save_signal(parsed, {"test": True})
            
            if signal_id:
                print(f"   ✅ Señal guardada con ID: {signal_id}")
                
                # Verificar que se puede recuperar
                recent = trading_db.get_recent_signals(hours=1)
                print(f"   📋 Señales recientes: {len(recent)}")
            else:
                print("   ❌ Error guardando señal")
        else:
            print("   ❌ No se pudo parsear señal para BD")
            
    except Exception as e:
        print(f"   ❌ Error en BD: {e}")

if __name__ == "__main__":
    asyncio.run(test_signal_processing())
    asyncio.run(test_database_save())