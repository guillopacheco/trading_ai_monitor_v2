# integrity_checker.py
import ast
import inspect
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrityChecker:
    """Verificador de integridad e integración de archivos"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.required_modules = [
            'main', 'signal_manager', 'trend_analysis', 'helpers', 
            'database', 'notifier', 'bybit_api', 'telegram_client',
            'health_monitor', 'operation_tracker', 'command_bot'
        ]
        
    def check_module_imports(self) -> Dict[str, List[str]]:
        """Verifica que todos los módulos puedan importarse"""
        results = {}
        
        for module_name in self.required_modules:
            try:
                module = importlib.import_module(module_name)
                results[module_name] = {
                    'status': '✅',
                    'classes': [cls for cls in dir(module) if not cls.startswith('_')],
                    'error': None
                }
                logger.info(f"✅ {module_name} - Importado correctamente")
            except Exception as e:
                results[module_name] = {
                    'status': '❌',
                    'classes': [],
                    'error': str(e)
                }
                logger.error(f"❌ {module_name} - Error: {e}")
                
        return results
    
    def check_method_completeness(self) -> Dict[str, Dict]:
        """Verifica que las clases tengan los métodos esperados"""
        expected_methods = {
            'SignalManager': [
                'process_new_signal', 'perform_technical_analysis',
                'make_trading_decision', '_create_analysis_summary',
                'get_pending_signals_count', 'get_signal_manager_stats'
            ],
            'TrendAnalyzer': [
                'analyze_signal', 'analyze_trend_confirmation',
                'get_analysis_summary'
            ],
            'TradingDatabase': [
                'save_signal', 'update_signal_status', 'get_recent_signals',
                'get_signal_stats', 'is_connected'
            ],
            'TelegramNotifier': [
                'send_signal_analysis', 'send_alert', 'test_connection'
            ]
        }
        
        results = {}
        
        for class_name, methods in expected_methods.items():
            try:
                # Buscar la clase en los módulos
                class_found = False
                missing_methods = []
                
                for module_name in self.required_modules:
                    try:
                        module = importlib.import_module(module_name)
                        if hasattr(module, class_name):
                            cls = getattr(module, class_name)
                            class_found = True
                            
                            # Verificar métodos
                            for method in methods:
                                if not hasattr(cls, method):
                                    missing_methods.append(method)
                            
                            break
                    except:
                        continue
                
                if class_found:
                    if missing_methods:
                        results[class_name] = {
                            'status': '⚠️',
                            'missing': missing_methods,
                            'message': f'Faltan {len(missing_methods)} métodos'
                        }
                    else:
                        results[class_name] = {
                            'status': '✅',
                            'missing': [],
                            'message': 'Completa'
                        }
                else:
                    results[class_name] = {
                        'status': '❌',
                        'missing': methods,
                        'message': 'Clase no encontrada'
                    }
                    
            except Exception as e:
                results[class_name] = {
                    'status': '❌',
                    'missing': methods,
                    'message': f'Error: {str(e)}'
                }
                
        return results
    
    def check_circular_imports(self) -> List[str]:
        """Detecta posibles importaciones circulares"""
        circular_warnings = []
        
        for module_name in self.required_modules:
            try:
                file_path = self.project_root / f"{module_name}.py"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Análisis simple de imports
                    tree = ast.parse(content)
                    imports = []
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.append(node.module)
                    
                    # Verificar imports problemáticos
                    for imp in imports:
                        if imp in self.required_modules:
                            # Verificar si el módulo importado también importa este
                            try:
                                imported_file = self.project_root / f"{imp}.py"
                                if imported_file.exists():
                                    with open(imported_file, 'r', encoding='utf-8') as f:
                                        imported_content = f.read()
                                    
                                    if f"import {module_name}" in imported_content or f"from {module_name}" in imported_content:
                                        circular_warnings.append(f"{module_name} <-> {imp}")
                            except:
                                pass
                                
            except Exception as e:
                logger.warning(f"Error analizando {module_name}: {e}")
                
        return list(set(circular_warnings))
    
    def check_file_sizes(self) -> Dict[str, int]:
        """Verifica que los archivos tengan contenido significativo"""
        sizes = {}
        
        for module_name in self.required_modules:
            file_path = self.project_root / f"{module_name}.py"
            if file_path.exists():
                size = file_path.stat().st_size
                sizes[module_name] = size
                status = "✅" if size > 1000 else "⚠️" if size > 100 else "❌"
                logger.info(f"{status} {module_name}.py - {size} bytes")
            else:
                sizes[module_name] = 0
                logger.error(f"❌ {module_name}.py - No existe")
                
        return sizes
    
    def run_complete_check(self):
        """Ejecuta verificación completa"""
        print("🔍 INICIANDO VERIFICACIÓN DE INTEGRIDAD")
        print("=" * 60)
        
        # 1. Verificar imports
        print("\n1. 📦 VERIFICANDO IMPORTS...")
        import_results = self.check_module_imports()
        
        # 2. Verificar métodos
        print("\n2. 🔧 VERIFICANDO MÉTODOS...")
        method_results = self.check_method_completeness()
        
        # 3. Verificar imports circulares
        print("\n3. 🔄 VERIFICANDO IMPORTS CIRCULARES...")
        circular_results = self.check_circular_imports()
        
        # 4. Verificar tamaños de archivos
        print("\n4. 📊 VERIFICANDO TAMAÑOS DE ARCHIVOS...")
        size_results = self.check_file_sizes()
        
        # Resumen
        print("\n" + "=" * 60)
        print("📋 RESUMEN DE VERIFICACIÓN")
        print("=" * 60)
        
        # Estadísticas de imports
        total_imports = len(import_results)
        successful_imports = sum(1 for r in import_results.values() if r['status'] == '✅')
        print(f"Imports: {successful_imports}/{total_imports} correctos")
        
        # Estadísticas de métodos
        total_classes = len(method_results)
        complete_classes = sum(1 for r in method_results.values() if r['status'] == '✅')
        print(f"Clases: {complete_classes}/{total_classes} completas")
        
        # Archivos problemáticos
        small_files = [mod for mod, size in size_results.items() if size < 500]
        if small_files:
            print(f"Archivos pequeños: {', '.join(small_files)}")
        
        if circular_results:
            print(f"Imports circulares: {', '.join(circular_results)}")
        
        # Recomendación
        if successful_imports == total_imports and complete_classes == total_classes and not circular_results:
            print("🎉 SISTEMA INTEGRO - Listo para producción")
            return True
        else:
            print("⚠️  SISTEMA CON PROBLEMAS - Revisar los issues arriba")
            return False

# Ejecutar verificación
if __name__ == "__main__":
    checker = IntegrityChecker()
    checker.run_complete_check()