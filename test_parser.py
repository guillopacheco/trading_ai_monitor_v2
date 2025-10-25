#!/usr/bin/env python3
"""
Prueba simple del parser de señales
"""
from helpers import parse_signal_message

test_signal = """🔥 #ENSO/USDT (Short📉, x20) 🔥
Entry - 1.538
Take-Profit:
🥉 1.5072 (40% of profit)
🥈 1.4919 (60% of profit)
🥇 1.4765 (80% of profit)
🚀 1.4611 (100% of profit)"""

print("🧪 Probando parser de señales...")
parsed = parse_signal_message(test_signal)

if parsed:
    print("✅ Parser funciona correctamente:")
    print(f"   Par: {parsed['pair']}")
    print(f"   Dirección: {parsed['direction']}")
    print(f"   Entry: {parsed['entry']}")
    print(f"   Leverage: x{parsed.get('leverage', 'N/A')}")
    print(f"   TPs: {parsed['tp1']}, {parsed['tp2']}, {parsed['tp3']}, {parsed['tp4']}")
    print(f"   % TPs: {parsed.get('tp1_percent', 'N/A')}%, {parsed.get('tp2_percent', 'N/A')}%, {parsed.get('tp3_percent', 'N/A')}%, {parsed.get('tp4_percent', 'N/A')}%")
else:
    print("❌ Parser falló")
