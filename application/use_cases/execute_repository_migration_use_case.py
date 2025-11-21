"""
Execute Repository Migration Use Case

Architectural Intent:
- Orchestrates repository-wide migration execution
- Applies refactoring across all files atomically
- Handles cross-file dependencies
"""

import os
from typing import Dict, List, Optional
from datetime import datetime

from domain.entities.repository import Repository, RepositoryStatus
from domain.value_objects.mar import MigrationAssessmentReport
from infrastructure.adapters.git_adapter import GitAdapter, create_git_adapter
from infrastructure.adapters.extended_semantic_engine import ExtendedSemanticRefactoringService
from infrastructure.adapters.extended_semantic_engine import create_extended_semantic_refactoring_engine
from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedSemanticRefactoringService
from infrastructure.adapters.azure_extended_semantic_engine import create_azure_extended_semantic_refactoring_engine
from infrastructure.adapters.dependency_graph_builder import DependencyGraphBuilder
from infrastructure.adapters.iac_migrator import IACMigrator
from infrastructure.adapters.test_execution_framework import TestExecutionFramework
from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter


class ExecuteRepositoryMigrationUseCase:
    """
    Use case for executing repository-wide migration
    """
    
    def __init__(self,
                 git_adapter: Optional[GitAdapter] = None,
                 refactoring_service: Optional[ExtendedSemanticRefactoringService] = None,
                 azure_refactoring_service: Optional[AzureExtendedSemanticRefactoringService] = None,
                 dependency_builder: Optional[DependencyGraphBuilder] = None,
                 iac_migrator: Optional[IACMigrator] = None,
                 repository_repo: Optional[RepositoryRepositoryAdapter] = None):
        self.git_adapter = git_adapter or GitAdapter()
        self.refactoring_service = refactoring_service or create_extended_semantic_refactoring_engine()
        self.azure_refactoring_service = azure_refactoring_service or create_azure_extended_semantic_refactoring_engine()
        self.dependency_builder = dependency_builder or DependencyGraphBuilder()
        self.iac_migrator = iac_migrator or IACMigrator()
        self.repository_repo = repository_repo or RepositoryRepositoryAdapter()
    
    def execute(self, repository_id: str, mar: MigrationAssessmentReport,
                services_to_migrate: Optional[List[str]] = None,
                run_tests: bool = False) -> Dict:
        """
        Execute repository migration based on MAR
        
        Args:
            repository_id: Repository identifier
            mar: Migration Assessment Report
            services_to_migrate: Optional list of specific services to migrate
            
        Returns:
            Dict with migration results
        """
        # Load repository
        repository = self.repository_repo.load(repository_id)
        if not repository or not repository.local_path:
            return {
                'success': False,
                'error': 'Repository not found or not cloned'
            }
        
        # Update status
        repository = repository.update_status(RepositoryStatus.MIGRATING)
        self.repository_repo.save(repository)
        
        try:
            # Determine services to migrate
            if services_to_migrate is None:
                services_to_migrate = mar.recommended_services or [s.service_name for s in mar.services_detected]
            
            # Get files to modify
            files_to_modify = mar.files_to_modify
            
            # Track changes
            files_changed = []
            files_failed = []
            
            # Migrate Infrastructure as Code files first
            iac_results = self.iac_migrator.migrate_all_iac_files(repository.local_path)
            for iac_file_path, (iac_content, iac_success) in iac_results.items():
                full_iac_path = os.path.join(repository.local_path, iac_file_path)
                try:
                    with open(full_iac_path, 'w', encoding='utf-8') as f:
                        f.write(iac_content)
                    if iac_success:
                        files_changed.append(iac_file_path)
                except Exception as e:
                    files_failed.append({
                        'file': iac_file_path,
                        'error': f'IaC migration failed: {str(e)}'
                    })
            
            # Apply refactoring to each code file
            for file_path in files_to_modify:
                full_path = os.path.join(repository.local_path, file_path)
                
                if not os.path.exists(full_path):
                    continue
                
                try:
                    # Read file
                    with open(full_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    # Determine language
                    language = 'python' if file_path.endswith('.py') else 'java'
                    
                    # Apply refactoring for each service
                    refactored_content = original_content
                    for service in mar.services_detected:
                        if service.service_name in services_to_migrate and file_path in service.files_affected:
                            # Determine service type and migration
                            if service.service_type == 'aws':
                                service_type = self._get_aws_service_type(service.service_name)
                                refactored_content = self.refactoring_service.apply_refactoring(
                                    source_code=refactored_content,
                                    language=language,
                                    service_type=service_type
                                )
                            elif service.service_type == 'azure':
                                service_type = self._get_azure_service_type(service.service_name)
                                refactored_content = self.azure_refactoring_service.apply_refactoring(
                                    source_code=refactored_content,
                                    language=language,
                                    service_type=service_type
                                )
                    
                    # Write refactored content if changed
                    if refactored_content != original_content:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(refactored_content)
                        files_changed.append(file_path)
                
                except Exception as e:
                    files_failed.append({
                        'file': file_path,
                        'error': str(e)
                    })
            
            # Run tests if requested
            test_results = None
            if run_tests:
                try:
                    test_framework = TestExecutionFramework(repository.local_path)
                    test_results = test_framework.execute_tests()
                    
                    # Store test results in metadata
                    repository.metadata['test_framework'] = test_results.framework.value
                    repository.metadata['test_total'] = str(test_results.total_tests)
                    repository.metadata['test_passed'] = str(test_results.passed)
                    repository.metadata['test_failed'] = str(test_results.failed)
                except Exception as e:
                    repository.metadata['test_error'] = str(e)
            
            # Update repository status
            migration_success = len(files_failed) == 0
            test_success = test_results is None or test_results.success if test_results else True
            
            if files_failed:
                repository = repository.update_status(RepositoryStatus.FAILED)
                repository.metadata['failed_files'] = str(len(files_failed))
            elif test_results and not test_results.success:
                repository = repository.update_status(RepositoryStatus.FAILED)
                repository.metadata['test_failures'] = str(test_results.failed)
            else:
                repository = repository.mark_migrated()
            
            repository.metadata['files_changed'] = str(len(files_changed))
            self.repository_repo.save(repository)
            
            result = {
                'success': migration_success and test_success,
                'repository_id': repository_id,
                'files_changed': files_changed,
                'files_failed': files_failed,
                'total_files_changed': len(files_changed),
                'total_files_failed': len(files_failed)
            }
            
            if test_results:
                result['test_results'] = {
                    'framework': test_results.framework.value,
                    'total_tests': test_results.total_tests,
                    'passed': test_results.passed,
                    'failed': test_results.failed,
                    'skipped': test_results.skipped,
                    'success': test_results.success
                }
            
            return result
            
        except Exception as e:
            repository = repository.update_status(RepositoryStatus.FAILED)
            repository.metadata['error'] = str(e)
            self.repository_repo.save(repository)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_aws_service_type(self, service_name: str) -> str:
        """Convert service name to service_type format"""
        service_mapping = {
            's3': 's3_to_gcs',
            'lambda': 'lambda_to_cloud_functions',
            'dynamodb': 'dynamodb_to_firestore',
            'sqs': 'sqs_to_pubsub',
            'sns': 'sns_to_pubsub',
        }
        return service_mapping.get(service_name, f'{service_name}_to_gcp')
    
    def _get_azure_service_type(self, service_name: str) -> str:
        """Convert service name to Azure service_type format"""
        service_mapping = {
            'blob_storage': 'azure_blob_storage_to_gcs',
            'functions': 'azure_functions_to_cloud_functions',
            'cosmos_db': 'azure_cosmos_db_to_firestore',
            'service_bus': 'azure_service_bus_to_pubsub',
        }
        return service_mapping.get(service_name, f'azure_{service_name}_to_gcp')
