# emergency_diagnostic.py
import asyncio
import logging
import sys
import os
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def emergency_diagnostic():
    """Diagnóstico de emergencia del sistema"""
    print("🚨 DIAGNÓSTICO DE EMERGENCIA - TRADING BOT")
    print("=" * 60)
    
    issues = []
    
    # 1. Verificar imports críticos
    print("1. 🔍 Verificando imports críticos...")
    try:
        from helpers import parse_signal_message
        print("   ✅ helpers.py - OK")
    except Exception as e:
        issues.append(f"❌ helpers.py: {e}")
        print(f"   ❌ helpers.py: {e}")
    
    try:
        from signal_manager import signal_manager
        print("   ✅ signal_manager.py - OK")
    except Exception as e:
        issues.append(f"❌ signal_manager.py: {e}")
        print(f"   ❌ signal_manager.py: {e}")
    
    try:
        from trend_analysis import trend_analyzer
        print("   ✅ trend_analysis.py - OK")
    except Exception as e:
        issues.append(f"❌ trend_analysis.py: {e}")
        print(f"   ❌ trend_analysis.py: {e}")
    
    # 2. Verificar configuración
    print("\n2. ⚙️ Verificando configuración...")
    try:
        from config import (
            BYBIT_API_KEY, BYBIT_API_SECRET, 
            TELEGRAM_BOT_TOKEN, SIGNALS_CHANNEL_ID
        )
        
        config_ok = True
        if not BYBIT_API_KEY or BYBIT_API_KEY == "TU_API_KEY_AQUI":
            issues.append("❌ BYBIT_API_KEY no configurada")
            config_ok = False
        if not TELEGRAM_BOT_TOKEN:
            issues.append("❌ TELEGRAM_BOT_TOKEN no configurado")
            config_ok = False
            
        if config_ok:
            print("   ✅ Configuración - OK")
        else:
            print("   ❌ Configuración - FALLANDO")
            
    except Exception as e:
        issues.append(f"❌ config.py: {e}")
        print(f"   ❌ config.py: {e}")
    
    # 3. Test de señal crítica
    print("\n3. 🧪 Test de procesamiento de señal...")
    test_signal = "🔥 #BTCUSDT LONG Entry: 50000 SL: 49000 TP: 51000"
    
    try:
        parsed = parse_signal_message(test_signal)
        if parsed:
            print(f"   ✅ Parser funciona: {parsed['pair']}")
            
            # Test de procesamiento
            success = await signal_manager.process_new_signal(parsed)
            print(f"   ✅ Signal Manager: {'OK' if success else 'FALLÓ'}")
        else:
            issues.append("❌ Parser no funciona")
            print("   ❌ Parser no funciona")
            
    except Exception as e:
        issues.append(f"❌ Procesamiento señal: {e}")
        print(f"   ❌ Procesamiento señal: {e}")
    
    # 4. Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DEL DIAGNÓSTICO:")
    print(f"   Total de issues: {len(issues)}")
    
    if issues:
        print("\n❌ PROBLEMAS ENCONTRADOS:")
        for issue in issues:
            print(f"   • {issue}")
        
        print(f"\n💡 RECOMENDACIÓN: Ejecutar solución de emergencia")
        return False
    else:
        print("✅ Sistema funcionando correctamente")
        return True

if __name__ == "__main__":
    result = asyncio.run(emergency_diagnostic())
    sys.exit(0 if result else 1)