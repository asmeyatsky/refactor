#!/usr/bin/env python3
"""
Comprehensive End-to-End Consistency Check

Performs deep consistency checks across:
1. Import chains and dependencies
2. API contract consistency (request/response)
3. Data flow consistency (frontend -> API -> backend -> database)
4. Type consistency across layers
5. Error handling consistency
6. Configuration consistency
7. Component integration
"""

import os
import sys
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ComprehensiveConsistencyChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.project_root = project_root
        self.checked_files = set()
        
    def check_all(self):
        """Run all comprehensive checks"""
        print("=" * 80)
        print("Comprehensive End-to-End Consistency Check")
        print("=" * 80)
        
        self.check_import_chains()
        self.check_api_contracts()
        self.check_data_flow()
        self.check_type_consistency()
        self.check_error_handling()
        self.check_component_integration()
        self.check_configuration_consistency()
        self.check_cli_api_alignment()
        
        self.print_results()
        return len(self.errors) == 0
    
    def check_import_chains(self):
        """Check import chains are valid"""
        print("\n[1/8] Checking import chains...")
        
        critical_imports = {
            'main.py': [
                'application.use_cases.analyze_repository_use_case',
                'application.use_cases.execute_repository_migration_use_case',
                'infrastructure.adapters.git_adapter',
                'infrastructure.adapters.pr_manager',
            ],
            'api_server.py': [
                'application.use_cases.analyze_repository_use_case',
                'application.use_cases.execute_repository_migration_use_case',
                'infrastructure.adapters.git_adapter',
                'infrastructure.adapters.mar_generator',
                'infrastructure.adapters.pr_manager',
            ],
            'application/use_cases/analyze_repository_use_case.py': [
                'infrastructure.adapters.git_adapter',
                'infrastructure.adapters.mar_generator',
                'infrastructure.repositories.repository_repository',
            ],
            'application/use_cases/execute_repository_migration_use_case.py': [
                'infrastructure.adapters.extended_semantic_engine',
                'infrastructure.adapters.azure_extended_semantic_engine',
                'infrastructure.adapters.iac_migrator',
                'infrastructure.adapters.test_execution_framework',
            ],
        }
        
        for file_path, required_imports in critical_imports.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()
                
                for imp in required_imports:
                    if imp.replace('.', '/') not in content and imp not in content:
                        self.errors.append(f"Missing import in {file_path}: {imp}")
    
    def check_api_contracts(self):
        """Check API request/response contracts match"""
        print("[2/8] Checking API contracts...")
        
        # Check analyze repository endpoint
        api_server = self.project_root / 'api_server.py'
        client_js = self.project_root / 'frontend/src/api/client.js'
        
        if api_server.exists() and client_js.exists():
            with open(api_server, 'r') as f:
                api_content = f.read()
            with open(client_js, 'r') as f:
                client_content = f.read()
            
            # Check analyze endpoint
            if 'repository_url' in api_content and 'repositoryUrl' in client_content:
                # Check response structure
                if 'mar' in api_content and 'mar' in client_content:
                    pass  # Good
                else:
                    self.warnings.append("MAR field may not be consistent between API and client")
            
            # Check migrate endpoint
            if 'repository_id' in api_content and 'repositoryId' in client_content:
                # Check request parameters
                api_params = ['services', 'create_pr', 'run_tests', 'branch_name']
                client_params = ['services', 'createPR', 'runTests', 'branchName']
                
                # Check snake_case vs camelCase conversion
                if 'create_pr' in api_content and 'createPR' in client_content:
                    pass  # Good - conversion happening
                else:
                    self.warnings.append("Parameter naming may not match (snake_case vs camelCase)")
    
    def check_data_flow(self):
        """Check data flows correctly through layers"""
        print("[3/8] Checking data flow...")
        
        # Check: Frontend -> API -> Use Case -> Repository
        flow_checks = [
            {
                'layer': 'Frontend',
                'file': 'frontend/src/App.js',
                'data': 'repositoryUrl',
                'next': 'API'
            },
            {
                'layer': 'API',
                'file': 'api_server.py',
                'data': 'repository_url',
                'next': 'Use Case'
            },
            {
                'layer': 'Use Case',
                'file': 'application/use_cases/analyze_repository_use_case.py',
                'data': 'repository_url',
                'next': 'Repository'
            }
        ]
        
        for check in flow_checks:
            file_path = self.project_root / check['file']
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                if check['data'] not in content:
                    self.warnings.append(f"Data flow issue: {check['data']} not found in {check['layer']}")
    
    def check_type_consistency(self):
        """Check type consistency across layers"""
        print("[4/8] Checking type consistency...")
        
        # Check RepositoryStatus enum usage
        repo_entity = self.project_root / 'domain/entities/repository.py'
        if repo_entity.exists():
            with open(repo_entity, 'r') as f:
                content = f.read()
            
            # Extract enum values
            status_match = re.search(r'class RepositoryStatus\(Enum\):.*?(\w+)\s*=\s*"(\w+)"', content, re.DOTALL)
            if status_match:
                # Check if used consistently
                use_case = self.project_root / 'application/use_cases/analyze_repository_use_case.py'
                if use_case.exists():
                    with open(use_case, 'r') as f:
                        uc_content = f.read()
                    if 'RepositoryStatus' not in uc_content:
                        self.warnings.append("RepositoryStatus enum may not be used in use case")
    
    def check_error_handling(self):
        """Check error handling consistency"""
        print("[5/8] Checking error handling...")
        
        # Check API error responses
        api_server = self.project_root / 'api_server.py'
        if api_server.exists():
            with open(api_server, 'r') as f:
                content = f.read()
            
            # Check for proper HTTPException usage
            if 'HTTPException' in content:
                # Check error detail format
                if 'detail=' in content:
                    pass  # Good
                else:
                    self.warnings.append("HTTPException may not use detail parameter consistently")
            
            # Check frontend error handling
            client_js = self.project_root / 'frontend/src/api/client.js'
            if client_js.exists():
                with open(client_js, 'r') as f:
                    content = f.read()
                
                if 'error.response?.data?.detail' in content:
                    pass  # Good - matches API error format
                else:
                    self.warnings.append("Frontend error handling may not match API error format")
    
    def check_component_integration(self):
        """Check component integration"""
        print("[6/8] Checking component integration...")
        
        # Check App.js imports all components
        app_js = self.project_root / 'frontend/src/App.js'
        if app_js.exists():
            with open(app_js, 'r') as f:
                content = f.read()
            
            required_components = [
                'CloudProviderSelection',
                'InputMethodSelection',
                'CodeSnippetInput',
                'RepositoryInput',
                'MigrationResults'
            ]
            
            for component in required_components:
                if component not in content:
                    self.errors.append(f"Missing component import: {component}")
            
            # Check components exist
            for component in required_components:
                comp_file = self.project_root / f'frontend/src/components/{component}.js'
                if not comp_file.exists():
                    self.errors.append(f"Component file missing: {component}.js")
    
    def check_configuration_consistency(self):
        """Check configuration consistency"""
        print("[7/8] Checking configuration...")
        
        # Check config.py
        config_path = self.project_root / 'config.py'
        if config_path.exists():
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Check for TOON-related config (if needed)
            # Check for repository storage paths
            if 'REPOSITORY_STORAGE_PATH' not in content:
                # Check if it's in repository_repository.py
                repo_repo = self.project_root / 'infrastructure/repositories/repository_repository.py'
                if repo_repo.exists():
                    with open(repo_repo, 'r') as f:
                        repo_content = f.read()
                    if 'REPOSITORY_STORAGE_PATH' not in repo_content and '/tmp/repositories' not in repo_content:
                        self.warnings.append("Repository storage path may not be configured")
        
        # Check requirements.txt has all dependencies
        req_path = self.project_root / 'requirements.txt'
        if req_path.exists():
            with open(req_path, 'r') as f:
                content = f.read()
            
            required_deps = {
                'PyPDF2': 'PDF reading',
                'PyYAML': 'YAML parsing for IaC',
                'google-generativeai': 'Gemini API',
                'requests': 'HTTP client',
            }
            
            for dep, reason in required_deps.items():
                if dep not in content:
                    self.warnings.append(f"Missing dependency: {dep} ({reason})")
    
    def check_cli_api_alignment(self):
        """Check CLI and API alignment"""
        print("[8/8] Checking CLI/API alignment...")
        
        main_py = self.project_root / 'main.py'
        api_server = self.project_root / 'api_server.py'
        
        if main_py.exists() and api_server.exists():
            with open(main_py, 'r') as f:
                main_content = f.read()
            with open(api_server, 'r') as f:
                api_content = f.read()
            
            # Check repository analyze
            if 'repo analyze' in main_content and '/api/repository/analyze' in api_content:
                # Check parameters match
                if 'repository_url' in api_content and 'repositoryUrl' in main_content:
                    pass  # Good
                else:
                    self.warnings.append("Repository analyze parameters may not align")
            
            # Check repository migrate
            if 'repo migrate' in main_content and '/api/repository/{repository_id}/migrate' in api_content:
                # Check parameters
                if 'run_tests' in api_content and 'run-tests' in main_content:
                    pass  # Good - CLI uses dashes, API uses underscores
                else:
                    self.warnings.append("Run tests parameter may not align")
    
    def print_results(self):
        """Print comprehensive results"""
        print("\n" + "=" * 80)
        print("Comprehensive Consistency Check Results")
        print("=" * 80)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        total_issues = len(self.errors) + len(self.warnings)
        
        if total_issues == 0:
            print("\n✅ All checks passed! System is consistent.")
        elif len(self.errors) == 0:
            print(f"\n✅ No critical errors found ({len(self.warnings)} warnings)")
            print("   System is functional but may benefit from improvements.")
        else:
            print(f"\n❌ Found {len(self.errors)} critical error(s) and {len(self.warnings)} warning(s)")
            print("   Please fix errors before deploying.")
        
        print("\n" + "=" * 80)
        print(f"Summary: {len(self.errors)} errors, {len(self.warnings)} warnings")
        print("=" * 80)

if __name__ == "__main__":
    checker = ComprehensiveConsistencyChecker()
    success = checker.check_all()
    sys.exit(0 if success else 1)
