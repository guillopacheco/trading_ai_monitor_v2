# dependency_mapper.py
import ast
import graphviz
from pathlib import Path

class DependencyMapper:
    """Genera mapa visual de dependencias"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.dependencies = {}
        
    def analyze_dependencies(self):
        """Analiza dependencias entre módulos"""
        py_files = list(self.project_root.glob("*.py"))
        
        for file_path in py_files:
            module_name = file_path.stem
            if module_name not in self.dependencies:
                self.dependencies[module_name] = set()
                
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                self.dependencies[module_name].add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                self.dependencies[module_name].add(node.module.split('.')[0])
                except:
                    continue
                    
        return self.dependencies
    
    def generate_graph(self, output_file: str = "dependencies"):
        """Genera gráfico de dependencias"""
        dot = graphviz.Digraph(comment='Dependencias del Proyecto')
        
        for module, deps in self.dependencies.items():
            dot.node(module)
            for dep in deps:
                if dep + '.py' in [f.name for f in self.project_root.glob("*.py")]:
                    dot.edge(module, dep)
        
        dot.render(output_file, format='png', cleanup=True)
        print(f"📊 Gráfico generado: {output_file}.png")
        
        return dot

if __name__ == "__main__":
    mapper = DependencyMapper()
    mapper.analyze_dependencies()
    mapper.generate_graph()