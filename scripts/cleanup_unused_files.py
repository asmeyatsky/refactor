#!/usr/bin/env python3
"""
Cleanup script to identify and remove unused files

Architectural Intent:
- This script helps maintain repository cleanliness
- Identifies temporary test files, outdated documentation, and unused code
- Follows Clean Architecture: Infrastructure-level utility script
"""

import os
import sys
from pathlib import Path
from typing import List, Set

# Files to keep (referenced in README or essential)
ESSENTIAL_FILES = {
    'README.md',
    'SKILL.md',
    'MIGRATION_GUIDE.md',
    'DEPLOYMENT.md',
    'QUICKSTART.md',
    'QUICK_DEPLOY.md',
    'REPOSITORY_LEVEL_MIGRATION.md',
    'CSHARP_MIGRATION_STATUS.md',
    'JAVA_MIGRATION_STATUS.md',
    'accelerator_detail.md',
    'CONTRIBUTING.md',
    'UNIVERSAL_CLOUD_REFACTOR_AGENT_PRD.md',
    'requirements.txt',
    'setup.py',
    'config.py',
    'main.py',
    'api_server.py',
    '.gitignore',
    '.env.example',
    'Dockerfile',
    'Dockerfile.cloudrun',
    'docker-compose.yml',
    'cloudbuild.yaml',
    'cloudrun-service.yaml',
    'cloudrun-deploy.sh',
    'deploy-now.sh',
    'deploy-with-secrets.sh',
    'start_api.sh',
}

# Test files to keep (comprehensive tests)
KEEP_TEST_FILES = {
    'test_aws_comprehensive.py',
    'test_java_comprehensive.py',
    'test_csharp_comprehensive.py',
    'test_code_snippets_comprehensive.py',
    'test_java_migrations.py',
    'test_csharp_migrations.py',
    'test_nodejs_validation.py',
    'test_golang_validation.py',
    'test_nodejs_golang_direct.py',
    'comprehensive_real_world_tests.py',
    'test_refactoring_output.py',
}

# Temporary/debugging test files to remove
TEMP_TEST_FILES = {
    'test_frozen_fix_final.py',
    'test_frozen_fix_simple.py',
    'test_frozen_fix_direct.py',
    'test_frozen_dataclass_fix.py',
    'test_direct_method.py',
    'test_standalone_function.py',
    'test_single_nodejs.py',
    'test_migration_direct.py',
    'test_java_simple.py',
}

# Outdated status/summary documentation to remove
OUTDATED_DOCS = {
    'API_SERVER_STATUS.md',
    'APIGEE_IMPLEMENTATION_SUMMARY.md',
    'AZURE_IMPLEMENTATION_SUMMARY.md',
    'COMPLETENESS_REPORT.md',
    'COMPLETION_SUMMARY.md',
    'COMPREHENSIVE_TEST_RESULTS.md',
    'CONSISTENCY_CHECK_REPORT.md',
    'CONSISTENCY_REPORT.md',
    'CSHARP_IMPLEMENTATION_SUMMARY.md',
    'CSHARP_TEST_CASES.md',
    'DEPLOYMENT_SUMMARY.md',
    'DOCUMENTATION_INDEX.md',
    'DOCUMENTATION_UPDATE_SUMMARY.md',
    'EKS_IMPLEMENTATION_SUMMARY.md',
    'EXTENDED_FEATURES_SUMMARY.md',
    'FARGATE_IMPLEMENTATION_SUMMARY.md',
    'FINAL_AUDIT_SUMMARY.md',
    'FINAL_REFINEMENT_SUMMARY.md',
    'FRONTEND_IMPROVEMENTS.md',
    'FRONTEND_SETUP.md',
    'FROZEN_DATACLASS_FIX_SUMMARY.md',
    'GCP_VARIABLES_REFERENCE.md',
    'gemini_api_analysis.md',
    'gemini_api_difference_analysis.md',
    'GEMINI_TOOLS_IMPLEMENTATION.md',
    'GIT_SETUP.md',
    'IMPORT_CHECK.md',
    'JAVA_TEST_CASES.md',
    'NODEJS_GOLANG_VALIDATION_SUMMARY.md',
    'PHASE_5_6_IMPLEMENTATION_SUMMARY.md',
    'REFACTORING_AUDIT_REPORT.md',
    'REPOSITORY_MIGRATION_IMPLEMENTATION_PLAN.md',
    'REPOSITORY_MIGRATION_IMPLEMENTATION_STATUS.md',
    'START_SERVICES.md',
    'STATUS_CHECK.md',
    'SYNTAX_VALIDATION_IMPLEMENTATION.md',
    'TEST_RESULTS.md',
    'TOON_IMPLEMENTATION_COMPLETE.md',
    'TOON_INTEGRATION_SUMMARY.md',
    'VALIDATION_TEST_RESULTS.md',
    'test_scenarios.md',
    'test_results_detailed.json',
    'test_api_request.json',
}


def find_files_to_remove(root_dir: Path) -> List[Path]:
    """Find files that should be removed"""
    files_to_remove = []
    
    for file_path in root_dir.rglob('*'):
        # Skip directories, git, node_modules, and hidden files
        if file_path.is_dir():
            continue
        if '.git' in file_path.parts:
            continue
        if 'node_modules' in file_path.parts:
            continue
        if file_path.name.startswith('.'):
            continue
        
        # Check if it's a temporary test file
        if file_path.name in TEMP_TEST_FILES:
            files_to_remove.append(file_path)
            continue
        
        # Check if it's outdated documentation
        if file_path.name in OUTDATED_DOCS:
            files_to_remove.append(file_path)
            continue
        
        # Skip essential files
        if file_path.name in ESSENTIAL_FILES:
            continue
        
        # Skip files in essential directories
        if any(part in ['domain', 'application', 'infrastructure', 'tests', 'frontend', 'scripts', 'examples'] 
               for part in file_path.parts):
            continue
    
    return files_to_remove


def main():
    """Main cleanup function"""
    import sys
    
    root_dir = Path(__file__).parent.parent
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    
    print("🔍 Scanning for unused files...")
    files_to_remove = find_files_to_remove(root_dir)
    
    if not files_to_remove:
        print("✅ No unused files found!")
        return
    
    print(f"\n📋 Found {len(files_to_remove)} files to remove:\n")
    for file_path in sorted(files_to_remove):
        print(f"  - {file_path.relative_to(root_dir)}")
    
    # Ask for confirmation unless auto-confirm
    if not auto_confirm:
        try:
            response = input(f"\n❓ Remove {len(files_to_remove)} files? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cleanup cancelled.")
                return
        except EOFError:
            print("⚠️  Running in non-interactive mode. Use --yes flag to auto-confirm.")
            return
    else:
        print(f"\n✅ Auto-confirmed: Removing {len(files_to_remove)} files...")
    
    # Remove files
    removed_count = 0
    for file_path in files_to_remove:
        try:
            file_path.unlink()
            removed_count += 1
            print(f"✅ Removed: {file_path.relative_to(root_dir)}")
        except Exception as e:
            print(f"❌ Failed to remove {file_path.relative_to(root_dir)}: {e}")
    
    print(f"\n✨ Cleanup complete! Removed {removed_count} files.")


if __name__ == "__main__":
    main()
