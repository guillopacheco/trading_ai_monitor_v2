# test_integration.py
import asyncio
import logging
from helpers import parse_signal_message, validate_signal_data
from signal_manager import signal_manager
from database import trading_db
from notifier import telegram_notifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationTester:
    """Prueba la integración entre módulos"""
    
    async def test_signal_flow(self):
        """Prueba el flujo completo de una señal"""
        print("🎯 TEST DE FLUJO DE SEÑAL COMPLETO")
        print("=" * 50)
        
        # 1. Señal de prueba
        test_signal = "🔥 #BTCUSDT LONG Entry: 50000 SL: 49000 TP: 51000, 52000, 53000"
        
        # 2. Parsear
        print("1. 📝 Parseando señal...")
        parsed = parse_signal_message(test_signal)
        if not parsed:
            print("❌ FALLO: No se pudo parsear la señal")
            return False
        print(f"   ✅ Parseada: {parsed['pair']} {parsed['direction']}")
        
        # 3. Validar
        print("2. ✅ Validando señal...")
        is_valid, message = validate_signal_data(parsed)
        if not is_valid:
            print(f"❌ FALLO: Señal inválida - {message}")
            return False
        print(f"   ✅ Válida: {message}")
        
        # 4. Procesar con Signal Manager
        print("3. 🔄 Procesando con Signal Manager...")
        try:
            success = await signal_manager.process_new_signal(parsed)
            if not success:
                print("❌ FALLO: Signal Manager no pudo procesar")
                return False
            print("   ✅ Procesada por Signal Manager")
        except Exception as e:
            print(f"❌ FALLO: Error en Signal Manager - {e}")
            return False
        
        # 5. Verificar en BD
        print("4. 💾 Verificando en base de datos...")
        recent = trading_db.get_recent_signals(hours=1)
        if not any(s['pair'] == parsed['pair'] for s in recent):
            print("❌ FALLO: Señal no guardada en BD")
            return False
        print(f"   ✅ Encontrada en BD: {len(recent)} señales recientes")
        
        # 6. Verificar estadísticas
        print("5. 📊 Verificando estadísticas...")
        stats = signal_manager.get_signal_manager_stats()
        print(f"   ✅ Stats: {stats}")
        
        # 7. Test de notificación (opcional)
        print("6. 📢 Probando notificación...")
        try:
            # Test simple de conexión
            if await telegram_notifier.test_connection():
                print("   ✅ Notificador funcionando")
            else:
                print("   ⚠️  Notificador con problemas")
        except Exception as e:
            print(f"   ⚠️  Error en notificador: {e}")
        
        print("\n🎉 FLUJO COMPLETADO EXITOSAMENTE")
        return True
    
    async def test_module_interactions(self):
        """Prueba interacciones específicas entre módulos"""
        print("\n🔄 TEST DE INTERACCIONES ENTRE MÓDULOS")
        print("=" * 50)
        
        tests = [
            ("SignalManager -> TrendAnalyzer", self._test_signal_trend_integration),
            ("SignalManager -> Database", self._test_signal_db_integration),
            ("Helpers -> SignalManager", self._test_helpers_signal_integration),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                success = await test_func()
                results.append((test_name, success))
                status = "✅" if success else "❌"
                print(f"{status} {test_name}")
            except Exception as e:
                results.append((test_name, False))
                print(f"❌ {test_name} - Error: {e}")
        
        return all(success for _, success in results)
    
    async def _test_signal_trend_integration(self):
        """Prueba integración SignalManager -> TrendAnalyzer"""
        from trend_analysis import trend_analyzer
        
        test_signal = {
            'pair': 'TESTUSDT',
            'direction': 'LONG',
            'entry': 100.0,
            'stop_loss': 95.0,
            'take_profits': [105.0, 110.0],
            'leverage': 10
        }
        
        analysis = trend_analyzer.analyze_signal(test_signal, 'TESTUSDT')
        return analysis is not None and 'recommendation' in analysis
    
    async def _test_signal_db_integration(self):
        """Prueba integración SignalManager -> Database"""
        test_signal = {
            'pair': 'TESTDBUSDT',
            'direction': 'SHORT',
            'entry': 50.0,
            'stop_loss': 55.0,
            'take_profits': [45.0, 40.0],
            'leverage': 5,
            'message_text': 'Test signal'
        }
        
        signal_id = trading_db.save_signal(test_signal, {
            'technical_analysis': {},
            'confirmation_result': {'status': 'TEST'},
            'analysis_summary': {'action': 'TEST'}
        })
        
        return signal_id is not None
    
    async def _test_helpers_signal_integration(self):
        """Prueba integración Helpers -> SignalManager"""
        test_message = "#INTEGRATIONTEST LONG Entry: 25.0"
        parsed = parse_signal_message(test_message)
        
        if not parsed:
            return False
            
        # Verificar que SignalManager puede procesar la salida de Helpers
        return await signal_manager.process_new_signal(parsed)

async def main():
    """Ejecuta todas las pruebas de integración"""
    tester = IntegrationTester()
    
    print("🚀 INICIANDO PRUEBAS DE INTEGRACIÓN COMPLETAS")
    print("=" * 60)
    
    # Ejecutar pruebas
    flow_success = await tester.test_signal_flow()
    integration_success = await tester.test_module_interactions()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN FINAL DE INTEGRACIÓN")
    print("=" * 60)
    
    if flow_success and integration_success:
        print("🎉 SISTEMA COMPLETAMENTE INTEGRADO")
        print("✅ Todos los módulos funcionan correctamente juntos")
        return True
    else:
        print("⚠️  SISTEMA CON PROBLEMAS DE INTEGRACIÓN")
        if not flow_success:
            print("❌ Flujo principal de señales falló")
        if not integration_success:
            print("❌ Algunas integraciones entre módulos fallaron")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)