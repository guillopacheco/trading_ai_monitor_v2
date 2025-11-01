# test_signal_futures.py
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

async def test_futures_signal_processing():
    """Prueba con símbolos de FUTURES (LINEAR)"""
    print("🎯 PRUEBA CON SÍMBOLOS DE FUTURES (LINEAR)")
    print("=" * 50)
    
    try:
        from signal_manager import signal_manager
        from helpers import parse_signal_message
        
        # Señal con símbolo de FUTURES
        test_signal = """
🔥 #BTCUSDT (Long📈, x20) 🔥

Entry - 50000.0
Stop-Loss - 49000.0
Take-Profit: 51000.0, 52000.0, 53000.0
"""
        
        print("1. 📝 Parseando señal BTCUSDT (Futures)...")
        parsed_signal = parse_signal_message(test_signal)
        
        if parsed_signal:
            print(f"   ✅ Parseada: {parsed_signal['pair']} {parsed_signal['direction']}")
            
            print("2. 🔍 Procesando con Signal Manager...")
            success = await signal_manager.process_new_signal(parsed_signal)
            
            if success:
                print("   ✅ Señal procesada exitosamente")
                stats = signal_manager.get_signal_manager_stats()
                print(f"   📊 Estadísticas: {stats}")
            else:
                print("   ❌ Error procesando señal")
        else:
            print("   ❌ No se pudo parsear la señal")
            
    except Exception as e:
        print(f"   ❌ Error en prueba: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_futures_symbols():
    """Prueba múltiples símbolos de futures"""
    print("\n3. 🔄 Probando múltiples símbolos FUTURES...")
    
    try:
        from signal_manager import signal_manager
        from helpers import parse_signal_message
        
        futures_signals = [
            "🔥 #ETHUSDT LONG Entry: 3500 SL: 3400 TP: 3600, 3700, 3800",
            "🎯 #SOLUSDT SHORT Entry: 150 SL: 155 TP: 145, 140, 135",
            "⚡ #ADAUSDT LONG Entry: 0.45 SL: 0.44 TP: 0.46, 0.47, 0.48"
        ]
        
        for i, signal_text in enumerate(futures_signals, 1):
            print(f"   📨 Procesando señal {i}...")
            parsed = parse_signal_message(signal_text)
            
            if parsed:
                print(f"      ✅ {parsed['pair']} {parsed['direction']}")
                success = await signal_manager.process_new_signal(parsed)
                print(f"      ✅ Procesada: {'Éxito' if success else 'Fallo'}")
            else:
                print(f"      ❌ No se pudo parsear")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO PRUEBAS CON FUTURES (LINEAR)")
    asyncio.run(test_futures_signal_processing())
    asyncio.run(test_multiple_futures_symbols())