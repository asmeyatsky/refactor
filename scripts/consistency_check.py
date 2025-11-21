#!/usr/bin/env python3
"""
End-to-End Consistency Check

Checks for:
1. Import consistency across modules
2. API endpoint consistency (frontend vs backend)
3. CLI command consistency
4. Domain/Application/Infrastructure layer consistency
5. Configuration consistency
6. Error handling consistency
7. Type consistency
"""

import os
import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ConsistencyChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.project_root = project_root
        
    def check_all(self):
        """Run all consistency checks"""
        print("=" * 80)
        print("End-to-End Consistency Check")
        print("=" * 80)
        
        self.check_imports()
        self.check_api_endpoints()
        self.check_cli_commands()
        self.check_domain_consistency()
        self.check_configuration()
        self.check_error_handling()
        self.check_type_consistency()
        
        self.print_results()
        return len(self.errors) == 0
    
    def check_imports(self):
        """Check import consistency"""
        print("\n[1/7] Checking imports...")
        
        # Check for missing imports
        critical_files = [
            'main.py',
            'api_server.py',
            'infrastructure/adapters/__init__.py',
            'application/use_cases/analyze_repository_use_case.py',
            'application/use_cases/execute_repository_migration_use_case.py',
        ]
        
        for file_path in critical_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    self.errors.append(f"Syntax error in {file_path}: {e}")
                except Exception as e:
                    self.warnings.append(f"Could not parse {file_path}: {e}")
    
    def check_api_endpoints(self):
        """Check API endpoint consistency between frontend and backend"""
        print("[2/7] Checking API endpoints...")
        
        # Backend endpoints
        backend_endpoints = set()
        api_server_path = project_root / 'api_server.py'
        if api_server_path.exists():
            with open(api_server_path, 'r') as f:
                content = f.read()
                # Find all @app.get/post/etc decorators
                for match in re.finditer(r'@app\.(get|post|put|delete)\("([^"]+)"', content):
                    endpoint = match.group(2)
                    backend_endpoints.add(endpoint)
        
        # Frontend API calls
        frontend_endpoints = set()
        client_path = project_root / 'frontend/src/api/client.js'
        if client_path.exists():
            with open(client_path, 'r') as f:
                content = f.read()
                # Find all API calls
                for match in re.finditer(r"['\"](/api/[^'\"]+)['\"]", content):
                    endpoint = match.group(1)
                    # Remove {repository_id} type placeholders
                    endpoint = re.sub(r'\{[^}]+\}', '{id}', endpoint)
                    frontend_endpoints.add(endpoint)
        
        # Check for mismatches
        missing_in_backend = frontend_endpoints - backend_endpoints
        missing_in_frontend = backend_endpoints - frontend_endpoints
        
        if missing_in_backend:
            self.errors.append(f"Frontend calls endpoints not in backend: {missing_in_backend}")
        if missing_in_frontend:
            self.warnings.append(f"Backend has endpoints not called by frontend: {missing_in_frontend}")
    
    def check_cli_commands(self):
        """Check CLI command consistency"""
        print("[3/7] Checking CLI commands...")
        
        main_path = project_root / 'main.py'
        if not main_path.exists():
            self.errors.append("main.py not found")
            return
        
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for required handlers
        required_handlers = [
            'handle_local_migration',
            'handle_repository_analyze',
            'handle_repository_migrate',
            'handle_repository_list'
        ]
        
        for handler in required_handlers:
            if handler not in content:
                self.errors.append(f"Missing CLI handler: {handler}")
        
        # Check command routing
        if 'args.repo_command' not in content:
            self.errors.append("Missing repo command routing logic")
    
    def check_domain_consistency(self):
        """Check domain layer consistency"""
        print("[4/7] Checking domain consistency...")
        
        # Check repository entity exists
        repo_entity = project_root / 'domain/entities/repository.py'
        if not repo_entity.exists():
            self.errors.append("Repository entity not found")
        
        # Check MAR value object exists
        mar_vo = project_root / 'domain/value_objects/mar.py'
        if not mar_vo.exists():
            self.errors.append("MAR value object not found")
        
        # Check use cases exist
        use_cases = [
            'application/use_cases/analyze_repository_use_case.py',
            'application/use_cases/execute_repository_migration_use_case.py'
        ]
        
        for uc_path in use_cases:
            full_path = project_root / uc_path
            if not full_path.exists():
                self.errors.append(f"Use case not found: {uc_path}")
    
    def check_configuration(self):
        """Check configuration consistency"""
        print("[5/7] Checking configuration...")
        
        # Check config.py has required fields
        config_path = project_root / 'config.py'
        if config_path.exists():
            with open(config_path, 'r') as f:
                content = f.read()
            
            required_configs = [
                'GEMINI_API_KEY',
                'LLM_PROVIDER',
            ]
            
            for config in required_configs:
                if config not in content:
                    self.warnings.append(f"Config {config} not found in config.py")
        
        # Check requirements.txt has new dependencies
        req_path = project_root / 'requirements.txt'
        if req_path.exists():
            with open(req_path, 'r') as f:
                content = f.read()
            
            required_deps = [
                'PyPDF2',
                'PyYAML',
            ]
            
            for dep in required_deps:
                if dep not in content:
                    self.warnings.append(f"Dependency {dep} not in requirements.txt")
    
    def check_error_handling(self):
        """Check error handling consistency"""
        print("[6/7] Checking error handling...")
        
        # Check Git adapter has proper error classes
        git_adapter = project_root / 'infrastructure/adapters/git_adapter.py'
        if git_adapter.exists():
            with open(git_adapter, 'r') as f:
                content = f.read()
            
            required_errors = [
                'GitAdapterError',
                'AuthenticationError',
                'RepositoryNotFoundError'
            ]
            
            for error in required_errors:
                if error not in content:
                    self.errors.append(f"Missing error class in git_adapter: {error}")
    
    def check_type_consistency(self):
        """Check type consistency"""
        print("[7/7] Checking type consistency...")
        
        # Check repository status enum values match
        repo_entity = project_root / 'domain/entities/repository.py'
        mar_vo = project_root / 'domain/value_objects/mar.py'
        
        if repo_entity.exists() and mar_vo.exists():
            with open(repo_entity, 'r') as f:
                repo_content = f.read()
            with open(mar_vo, 'r') as f:
                mar_content = f.read()
            
            # Check RepositoryStatus enum values are used consistently
            status_values = re.findall(r'RepositoryStatus\.(\w+)', repo_content)
            if status_values:
                # Check if MAR uses same status values
                for status in status_values:
                    if status.upper() not in mar_content and status not in mar_content:
                        self.warnings.append(f"RepositoryStatus.{status} may not be used consistently")
    
    def print_results(self):
        """Print check results"""
        print("\n" + "=" * 80)
        print("Consistency Check Results")
        print("=" * 80)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All checks passed!")
        elif not self.errors:
            print(f"\n✅ No errors found ({len(self.warnings)} warnings)")
        else:
            print(f"\n❌ Found {len(self.errors)} error(s) and {len(self.warnings)} warning(s)")
        
        print("=" * 80)

if __name__ == "__main__":
    checker = ConsistencyChecker()
    success = checker.check_all()
    sys.exit(0 if success else 1)
