# test_signal_direct.py
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_signal_processing():
    """Prueba el procesamiento de señales directamente"""
    print("🎯 PRUEBA DIRECTA DE PROCESAMIENTO DE SEÑALES ICNT/USDT")
    print("=" * 60)
    
    try:
        # Importar componentes
        from signal_manager import signal_manager
        from helpers import parse_signal_message
        
        # Señal específica de ICNT/USDT
        test_signal = """
🔥 #ICNT/USDT (Long📈, x20) 🔥

Entry - 0.3197
Take-Profit:

🥉 0.3261 (40% of profit)
🥈 0.3293 (60% of profit)
🥇 0.3325 (80% of profit)
🚀 0.3357 (100% of profit)
"""
        
        print("1. 📝 Parseando señal ICNT/USDT...")
        print(f"   Texto de señal: {test_signal}")
        
        parsed_signal = parse_signal_message(test_signal)
        
        if parsed_signal:
            print(f"   ✅ Parseada: {parsed_signal['pair']} {parsed_signal['direction']} @ {parsed_signal['entry']}")
            print(f"   📊 Detalles:")
            print(f"      - Stop Loss: {parsed_signal.get('stop_loss', 'N/A')}")
            print(f"      - Take Profits: {parsed_signal.get('take_profits', 'N/A')}")
            print(f"      - Leverage: {parsed_signal.get('leverage', 'N/A')}")
            
            print("2. 🔍 Procesando con Signal Manager...")
            
            # Verificar que signal_manager tenga los métodos necesarios
            if hasattr(signal_manager, 'process_new_signal'):
                success = await signal_manager.process_new_signal(parsed_signal)
                
                if success:
                    print("   ✅ Señal procesada exitosamente")
                    print("   📊 Estadísticas del Signal Manager:")
                    stats = signal_manager.get_signal_manager_stats()
                    print(f"      - Señales procesadas: {stats['signals_processed']}")
                    print(f"      - Señales pendientes: {stats['pending_signals']}")
                    print(f"      - Tasa de éxito: {stats['success_rate']:.1f}%")
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
        
        test_signal = "🔥 #ICNT/USDT (Short📉, x5) 🔥\n**Entry** - 0.3250"
        parsed = parse_signal_message(test_signal)
        
        if parsed:
            # Guardar directamente en BD
            signal_id = trading_db.save_signal(parsed, {
                "test": True,
                "test_timestamp": datetime.now().isoformat(),
                "signal_type": "test_ICNT"
            })
            
            if signal_id:
                print(f"   ✅ Señal ICNT guardada con ID: {signal_id}")
                
                # Verificar que se puede recuperar
                recent = trading_db.get_recent_signals(hours=1)
                icnt_signals = [s for s in recent if 'ICNT' in s.get('pair', '')]
                print(f"   📋 Señales ICNT recientes: {len(icnt_signals)}")
                
                # Mostrar detalles de señales ICNT
                for signal in icnt_signals[:3]:  # Mostrar primeras 3
                    print(f"      - {signal.get('pair')} {signal.get('direction')} @ {signal.get('entry_price')}")
            else:
                print("   ❌ Error guardando señal")
        else:
            print("   ❌ No se pudo parsear señal para BD")
            
    except Exception as e:
        print(f"   ❌ Error en BD: {e}")

async def test_multiple_icnt_signals():
    """Prueba múltiples señales de ICNT con diferentes formatos"""
    print("\n4. 🔄 Probando múltiples formatos de señales ICNT...")
    
    try:
        from signal_manager import signal_manager
        from helpers import parse_signal_message
        
        test_signals = [
            # Formato original
            """
🔥 #ICNT/USDT (Long📈, x20) 🔥

Entry - 0.3197
Take-Profit:

🥉 0.3261 (40% of profit)
🥈 0.3293 (60% of profit)
🥇 0.3325 (80% of profit)
🚀 0.3357 (100% of profit)
""",
            # Formato simplificado
            "🔥 #ICNT/USDT LONG Entry: 0.3200 SL: 0.3150 TP: 0.3250, 0.3300, 0.3350",
            # Formato con stop loss explícito
            """
🎯 #ICNT/USDT SHORT 🎯
ENTRY: 0.3250
LEVERAGE: 10x
TP: 0.3200, 0.3150, 0.3100
SL: 0.3300
"""
        ]
        
        for i, signal_text in enumerate(test_signals, 1):
            print(f"   📨 Procesando señal {i}...")
            parsed = parse_signal_message(signal_text)
            
            if parsed:
                print(f"      ✅ Parseada: {parsed['pair']} {parsed['direction']}")
                success = await signal_manager.process_new_signal(parsed)
                print(f"      ✅ Procesada: {'Éxito' if success else 'Fallo'}")
            else:
                print(f"      ❌ No se pudo parsear señal {i}")
                
    except Exception as e:
        print(f"   ❌ Error en prueba múltiple: {e}")

async def test_analysis_details():
    """Prueba obtener detalles del análisis"""
    print("\n5. 📊 Obteniendo detalles del análisis...")
    
    try:
        from database import trading_db
        
        # Obtener señales recientes de ICNT
        recent = trading_db.get_recent_signals(hours=24)
        icnt_signals = [s for s in recent if 'ICNT' in s.get('pair', '')]
        
        print(f"   📈 Señales ICNT en BD (24h): {len(icnt_signals)}")
        
        for signal in icnt_signals:
            signal_id = signal.get('id')
            analysis = trading_db.get_signal_analysis(signal_id)
            
            if analysis and analysis.get('analysis_summary'):
                summary = analysis['analysis_summary']
                print(f"      🔍 Señal {signal_id}:")
                print(f"         - Acción: {summary.get('action', 'N/A')}")
                print(f"         - Confianza: {summary.get('confidence', 'N/A')}")
                print(f"         - Match: {summary.get('match_percentage', 'N/A')}%")
                
    except Exception as e:
        print(f"   ❌ Error obteniendo análisis: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO PRUEBAS COMPLETAS PARA ICNT/USDT")
    print("=" * 60)
    
    asyncio.run(test_signal_processing())
    asyncio.run(test_database_save())
    asyncio.run(test_multiple_icnt_signals())
    asyncio.run(test_analysis_details())
    
    print("\n" + "=" * 60)
    print("🎉 PRUEBAS COMPLETADAS")
    print("=" * 60)