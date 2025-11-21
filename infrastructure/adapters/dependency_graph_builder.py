"""
Dependency Graph Builder

Architectural Intent:
- Builds cross-file dependency graphs for codebases
- Tracks imports, exports, constants, and variable dependencies
- Supports Python and Java initially
"""

import os
import ast
import re
from typing import List, Dict, Set, Optional
from collections import defaultdict

from domain.value_objects.mar import CrossFileDependency


class DependencyGraphBuilder:
    """
    Builds dependency graphs for codebases
    
    Analyzes imports, exports, and cross-file references to build
    a comprehensive dependency graph.
    """
    
    def __init__(self):
        self.dependencies: List[CrossFileDependency] = []
        self.imports_map: Dict[str, List[str]] = defaultdict(list)  # file -> imports
        self.exports_map: Dict[str, List[str]] = defaultdict(list)  # file -> exports
    
    def build_graph(self, repository_path: str, languages: List[str]) -> List[CrossFileDependency]:
        """
        Build dependency graph for repository
        
        Args:
            repository_path: Path to repository root
            languages: List of languages to analyze (e.g., ['python', 'java'])
            
        Returns:
            List of CrossFileDependency objects
        """
        self.dependencies = []
        self.imports_map.clear()
        self.exports_map.clear()
        
        # Find all code files
        code_files = self._find_code_files(repository_path, languages)
        
        # Build imports and exports for each file
        for file_path in code_files:
            if 'python' in languages:
                self._analyze_python_file(file_path, repository_path)
            if 'java' in languages:
                self._analyze_java_file(file_path, repository_path)
        
        # Build cross-file dependencies
        self._build_cross_file_dependencies(code_files, repository_path)
        
        return self.dependencies
    
    def _find_code_files(self, repo_path: str, languages: List[str]) -> List[str]:
        """Find all code files in repository"""
        code_files = []
        extensions = []
        
        if 'python' in languages:
            extensions.extend(['.py'])
        if 'java' in languages:
            extensions.extend(['.java'])
        
        for root, dirs, files in os.walk(repo_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target', '.idea']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    code_files.append(os.path.join(root, file))
        
        return code_files
    
    def _analyze_python_file(self, file_path: str, repo_path: str) -> None:
        """Analyze Python file for imports and exports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=file_path)
            relative_path = os.path.relpath(file_path, repo_path)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
            
            self.imports_map[relative_path] = imports
            
            # Extract exports (top-level functions, classes, constants)
            exports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not node.name.startswith('_'):
                        exports.append(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and not target.id.startswith('_'):
                            exports.append(target.id)
            
            self.exports_map[relative_path] = exports
            
        except SyntaxError:
            # Skip files with syntax errors
            pass
        except Exception:
            # Skip files that can't be parsed
            pass
    
    def _analyze_java_file(self, file_path: str, repo_path: str) -> None:
        """Analyze Java file for imports and exports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            relative_path = os.path.relpath(file_path, repo_path)
            
            # Extract imports
            imports = []
            import_pattern = r'import\s+([\w.]+)'
            for match in re.finditer(import_pattern, content):
                import_name = match.group(1)
                # Extract package name (first part)
                package = import_name.split('.')[0]
                imports.append(package)
            
            self.imports_map[relative_path] = imports
            
            # Extract exports (public classes, interfaces, enums)
            exports = []
            # Match public class/interface/enum declarations
            export_pattern = r'public\s+(class|interface|enum)\s+(\w+)'
            for match in re.finditer(export_pattern, content):
                exports.append(match.group(2))
            
            self.exports_map[relative_path] = exports
            
        except Exception:
            # Skip files that can't be parsed
            pass
    
    def _build_cross_file_dependencies(self, code_files: List[str], repo_path: str) -> None:
        """Build cross-file dependency relationships"""
        # Create a map of module names to file paths
        module_to_file = {}
        for file_path in code_files:
            relative_path = os.path.relpath(file_path, repo_path)
            module_name = self._get_module_name(relative_path)
            module_to_file[module_name] = relative_path
        
        # Build dependencies based on imports
        for file_path in code_files:
            relative_path = os.path.relpath(file_path, repo_path)
            imports = self.imports_map.get(relative_path, [])
            
            for imported_module in imports:
                # Try to find the file that exports this module
                target_file = self._find_target_file(imported_module, module_to_file, relative_path)
                
                if target_file and target_file != relative_path:
                    # Check if this dependency already exists
                    existing = next(
                        (d for d in self.dependencies 
                         if d.source_file == relative_path and d.target_file == target_file),
                        None
                    )
                    
                    if existing:
                        # Update usage count
                        self.dependencies.remove(existing)
                        self.dependencies.append(CrossFileDependency(
                            source_file=relative_path,
                            target_file=target_file,
                            dependency_type='import',
                            dependency_name=imported_module,
                            usage_count=existing.usage_count + 1
                        ))
                    else:
                        self.dependencies.append(CrossFileDependency(
                            source_file=relative_path,
                            target_file=target_file,
                            dependency_type='import',
                            dependency_name=imported_module,
                            usage_count=1
                        ))
    
    def _get_module_name(self, file_path: str) -> str:
        """Extract module name from file path"""
        # Remove extension
        module_name = os.path.splitext(file_path)[0]
        # Replace path separators with dots
        module_name = module_name.replace(os.sep, '.').replace('/', '.')
        # Remove leading dots
        module_name = module_name.lstrip('.')
        return module_name
    
    def _find_target_file(self, module_name: str, module_to_file: Dict[str, str], 
                         current_file: str) -> Optional[str]:
        """Find target file for an imported module"""
        # Direct match
        if module_name in module_to_file:
            return module_to_file[module_name]
        
        # Try partial matches (for relative imports)
        for module, file_path in module_to_file.items():
            if module.endswith(module_name) or module_name in module.split('.'):
                return file_path
        
        # Try to find file with matching name
        module_base = module_name.split('.')[-1]
        for module, file_path in module_to_file.items():
            if module_base in file_path or module_base == os.path.splitext(os.path.basename(file_path))[0]:
                return file_path
        
        return None
    
    def get_dependencies_for_file(self, file_path: str) -> List[CrossFileDependency]:
        """Get all dependencies for a specific file"""
        return [d for d in self.dependencies if d.source_file == file_path]
    
    def get_files_depending_on(self, file_path: str) -> List[CrossFileDependency]:
        """Get all files that depend on a specific file"""
        return [d for d in self.dependencies if d.target_file == file_path]
