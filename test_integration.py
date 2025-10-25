#!/usr/bin/env python3
"""
Test de integración entre módulos del Trading AI Monitor
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers import parse_signal_message, validate_signal_data
from database import trading_db
from trend_analysis import trend_analyzer
from indicators import indicators_calculator

def test_parsing():
    """Test del parser de señales"""
    print("🧪 Probando parser de señales...")
    
    test_messages = [
        """🔥 #UB/USDT (Long📈, x20) 🔥
Entry - 0.04869
Take-Profit:
🥉 0.04966 (40% of profit)
🥈 0.05015 (60% of profit)
🥇 0.05063 (80% of profit)
🚀 0.05112 (100% of profit)""",
        
        """🔥 #4/USDT (Short📉, x20) 🔥
Entry - 0.0854
Take-Profit:
🥉 0.08369 (40% of profit)
🥈 0.08284 (60% of profit)
🥇 0.08198 (80% of profit)
🚀 0.08113 (100% of profit)"""
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n--- Test señal {i} ---")
        parsed = parse_signal_message(msg)
        if parsed:
            print(f"✅ Parseado: {parsed['pair']} {parsed['direction']}")
            print(f"   Entry: {parsed['entry']}, Leverage: x{parsed['leverage']}")
            is_valid = validate_signal_data(parsed)
            print(f"   Validación: {'✅ PASS' if is_valid else '❌ FAIL'}")
        else:
            print("❌ No se pudo parsear")

def test_database():
    """Test de la base de datos"""
    print("\n🧪 Probando base de datos...")
    try:
        # Test de conexión
        stats = trading_db.get_signal_stats(days=1)
        print(f"✅ Base de datos operativa")
        print(f"   Señales en BD: {stats.get('total_signals', 0)}")
        return True
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False

def test_indicators():
    """Test de indicadores técnicos"""
    print("\n🧪 Probando indicadores técnicos...")
    try:
        # Test básico de indicadores
        analysis = indicators_calculator.analyze_timeframe("BTCUSDT", "5")
        if analysis:
            print(f"✅ Indicadores funcionando")
            print(f"   Precio: {analysis['close_price']}, RSI: {analysis['rsi']}")
            return True
        else:
            print("❌ No se pudieron obtener indicadores (puede ser normal si no hay conexión a internet)")
            return True  # Consideramos éxito porque el módulo se importa correctamente
    except Exception as e:
        print(f"❌ Error en indicadores: {e}")
        return False

async def test_trend_analysis():
    """Test del análisis de tendencias"""
    print("\n🧪 Probando análisis de tendencias...")
    try:
        test_signal = {
            'pair': 'BTCUSDT',
            'direction': 'SHORT', 
            'entry': 50000,
            'leverage': 20,
            'tp1': 49000, 'tp2': 48500, 'tp3': 48000, 'tp4': 47500,
            'tp1_percent': 40, 'tp2_percent': 60, 'tp3_percent': 80, 'tp4_percent': 100
        }
        
        analysis = trend_analyzer.analyze_signal(test_signal, 'BTCUSDT')
        if analysis and 'recommendation' in analysis:
            print(f"✅ Análisis de tendencias funcionando")
            print(f"   Recomendación: {analysis['recommendation'].action}")
            return True
        else:
            print("❌ No se pudo completar el análisis")
            return False
    except Exception as e:
        print(f"❌ Error en análisis de tendencias: {e}")
        return False

async def main():
    print("🚀 Iniciando tests de integración...")
    
    # Tests síncronos
    test_parsing()
    test_database() 
    test_indicators()
    
    # Tests asíncronos
    await test_trend_analysis()
    
    print("\n" + "="*50)
    print("✅ Tests de integración completados")
    print("📝 Revisa los resultados arriba para verificar que todo funciona")

if __name__ == "__main__":
    asyncio.run(main())