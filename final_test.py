#!/usr/bin/env python3
"""
Prueba final del sistema completo
"""
import sys
import pandas as pd
import numpy as np

print("🧪 PRUEBA FINAL DEL SISTEMA COMPLETO")
print("=" * 50)

# Verificar dependencias principales
dependencies = [
    ("pandas", "pd"),
    ("numpy", "np"),
    ("scipy", "scipy"),
    ("telegram", "telegram"),
    ("telethon", "telethon"),
    ("requests", "requests"),
    ("pandas_ta", "ta"),
    ("aiohttp", "aiohttp"),
]

print("📦 VERIFICANDO DEPENDENCIAS:")
all_ok = True
for dep, alias in dependencies:
    try:
        __import__(dep)
        print(f"   ✅ {dep} - OK")
    except ImportError as e:
        print(f"   ❌ {dep} - FALLÓ: {e}")
        all_ok = False

print(f"\n📊 VERSIONES:")
try:
    print(f"   numpy: {np.__version__}")
    print(f"   pandas: {pd.__version__}")
    import scipy
    print(f"   scipy: {scipy.__version__}")
except Exception as e:
    print(f"   Error obteniendo versiones: {e}")

print(f"\n🎯 PROBANDO INDICADORES TÉCNICOS:")
try:
    # Crear datos de prueba más realistas
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'open': np.random.uniform(100, 200, 100),
        'high': np.random.uniform(200, 250, 100),
        'low': np.random.uniform(50, 100, 100),
        'close': np.random.uniform(100, 150, 100),
        'volume': np.random.uniform(1000, 10000, 100)
    })
    
    import pandas_ta as ta
    
    # Probar RSI
    rsi = ta.rsi(df['close'], length=14)
    if rsi is not None and not rsi.isna().all():
        print(f"   ✅ RSI: {rsi.iloc[-1]:.2f}")
    else:
        print("   ⚠️  RSI: No calculado (pocos datos)")
    
    # Probar EMA
    ema = ta.ema(df['close'], length=20)
    if ema is not None and not ema.isna().all():
        print(f"   ✅ EMA: {ema.iloc[-1]:.2f}")
    else:
        print("   ⚠️  EMA: No calculado")
    
    # Probar MACD
    macd_data = ta.macd(df['close'])
    if macd_data is not None:
        print(f"   ✅ MACD: Calculado correctamente")
    else:
        print("   ⚠️  MACD: No calculado")
    
    # Probar ATR
    atr = ta.atr(df['high'], df['low'], df['close'])
    if atr is not None and not atr.isna().all():
        print(f"   ✅ ATR: {atr.iloc[-1]:.2f}")
    else:
        print("   ⚠️  ATR: No calculado")
        
except Exception as e:
    print(f"   ❌ Error en indicadores: {e}")
    all_ok = False

print(f"\n🔧 PROBANDO MÓDULOS DEL SISTEMA:")
try:
    from helpers import parse_signal_message
    
    test_signal = """🔥 #BTC/USDT (Short📉, x20) 🔥
Entry - 50000
Take-Profit:
🥉 49000 (40% of profit)
🥈 48500 (60% of profit)
🥇 48000 (80% of profit)
🚀 47500 (100% of profit)"""
    
    parsed = parse_signal_message(test_signal)
    if parsed:
        print(f"   ✅ Parser de señales: OK")
        print(f"      Par: {parsed['pair']}")
        print(f"      Dirección: {parsed['direction']}")
        print(f"      Entry: {parsed['entry']}")
        print(f"      Leverage: x{parsed.get('leverage', 'N/A')}")
    else:
        print("   ❌ Parser de señales: FALLÓ")
        all_ok = False
        
except Exception as e:
    print(f"   ❌ Parser de señales: {e}")
    all_ok = False

print(f"\n🎯 PROBANDO GESTIÓN DE RIESGO:")
try:
    from helpers import calculate_position_size
    
    position_info = calculate_position_size(
        entry_price=50000,
        stop_loss=49000,
        account_balance=1000,
        leverage=20
    )
    
    if position_info:
        print(f"   ✅ Gestión de riesgo: OK")
        print(f"      Tamaño posición: {position_info['position_size']} USDT")
        print(f"      Riesgo real: {position_info['real_risk_percent']}%")
    else:
        print("   ❌ Gestión de riesgo: FALLÓ")
        
except Exception as e:
    print(f"   ❌ Gestión de riesgo: {e}")
    all_ok = False

print("\n" + "=" * 50)
if all_ok:
    print("🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
    print("🚀 Puedes proceder con las pruebas reales")
else:
    print("⚠️  Hay algunos problemas que resolver")
    print("💡 Revisa los errores arriba")

print("\n📝 PRÓXIMOS PASOS:")
print("   1. Configurar archivo .env con tus tokens de Telegram")
print("   2. Ejecutar: python scripts/test_telegram_setup.py")
print("   3. Ejecutar: python main.py")
