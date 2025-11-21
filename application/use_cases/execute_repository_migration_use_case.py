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
            print(f"Files to modify: {files_to_modify}")
            print(f"Services to migrate: {services_to_migrate}")
            print(f"Repository local path: {repository.local_path}")
            
            for file_path in files_to_modify:
                full_path = os.path.join(repository.local_path, file_path)
                print(f"Processing file: {file_path} -> {full_path}")
                
                if not os.path.exists(full_path):
                    print(f"WARNING: File not found: {full_path}")
                    files_failed.append({
                        'file': file_path,
                        'error': f'File not found at path: {full_path}'
                    })
                    continue
                
                try:
                    # Read file
                    with open(full_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    print(f"Read {len(original_content)} characters from {file_path}")
                    
                    # Determine language
                    language = 'python' if file_path.endswith('.py') else 'java'
                    print(f"Detected language: {language}")
                    
                    # Apply refactoring for each service
                    refactored_content = original_content
                    services_applied = []
                    
                    print(f"Checking {len(mar.services_detected)} detected services against {len(services_to_migrate)} services to migrate")
                    for service in mar.services_detected:
                        print(f"  Service: {service.service_name}, type: {service.service_type}, files_affected: {service.files_affected}")
                        print(f"    In services_to_migrate? {service.service_name in services_to_migrate}")
                        print(f"    File in files_affected? {file_path in service.files_affected}")
                        
                        if service.service_name in services_to_migrate and file_path in service.files_affected:
                            print(f"✅ Applying refactoring for service: {service.service_name} (type: {service.service_type})")
                            # Determine service type and migration
                            if service.service_type == 'aws':
                                service_type = self._get_aws_service_type(service.service_name)
                                print(f"  AWS service type: {service_type}")
                                try:
                                    # CRITICAL: Run aggressive AWS cleanup BEFORE apply_refactoring
                                    if language == 'python' and hasattr(self.refactoring_service.ast_engine, '_aggressive_aws_cleanup'):
                                        refactored_content = self.refactoring_service.ast_engine._aggressive_aws_cleanup(refactored_content)
                                    
                                    refactored_result = self.refactoring_service.apply_refactoring(
                                        source_code=refactored_content,
                                        language=language,
                                        service_type=service_type
                                    )
                                    
                                    # CRITICAL: Run aggressive AWS cleanup AFTER apply_refactoring
                                    if language == 'python' and hasattr(self.refactoring_service.ast_engine, '_aggressive_aws_cleanup'):
                                        if isinstance(refactored_result, tuple):
                                            refactored_result = (self.refactoring_service.ast_engine._aggressive_aws_cleanup(refactored_result[0]), refactored_result[1])
                                        else:
                                            refactored_result = self.refactoring_service.ast_engine._aggressive_aws_cleanup(refactored_result)
                                    # Ensure we have a string, not a tuple
                                    if isinstance(refactored_result, tuple):
                                        refactored_content, _ = refactored_result
                                    else:
                                        refactored_content = refactored_result
                                    
                                    # Validate it's a string
                                    if not isinstance(refactored_content, str):
                                        raise TypeError(f"Expected string, got {type(refactored_content)}: {refactored_content}")
                                    
                                    services_applied.append(service.service_name)
                                    print(f"  ✅ Successfully applied refactoring for {service.service_name}")
                                except Exception as e:
                                    print(f"  ❌ Error applying refactoring: {e}")
                                    import traceback
                                    print(f"  Traceback: {traceback.format_exc()}")
                                    raise
                            elif service.service_type == 'azure':
                                service_type = self._get_azure_service_type(service.service_name)
                                print(f"  Azure service type: {service_type}")
                                try:
                                    refactored_result = self.azure_refactoring_service.apply_refactoring(
                                        source_code=refactored_content,
                                        language=language,
                                        service_type=service_type
                                    )
                                    # Ensure we have a string, not a tuple
                                    if isinstance(refactored_result, tuple):
                                        refactored_content, _ = refactored_result
                                    else:
                                        refactored_content = refactored_result
                                    
                                    # Validate it's a string
                                    if not isinstance(refactored_content, str):
                                        raise TypeError(f"Expected string, got {type(refactored_result)}: {refactored_result}")
                                    
                                    services_applied.append(service.service_name)
                                    print(f"  ✅ Successfully applied refactoring for {service.service_name}")
                                except Exception as e:
                                    print(f"  ❌ Error applying refactoring: {e}")
                                    import traceback
                                    print(f"  Traceback: {traceback.format_exc()}")
                                    raise
                        else:
                            print(f"  ⏭️  Skipping service {service.service_name} (not in services_to_migrate or file not affected)")
                    
                    print(f"Services applied: {services_applied}")
                    print(f"Content changed: {refactored_content != original_content}")
                    
                    # Final validation: ensure refactored_content is a string before writing
                    if not isinstance(refactored_content, str):
                        raise TypeError(
                            f"refactored_content must be a string, got {type(refactored_content)}. "
                            f"Value: {str(refactored_content)[:200]}"
                        )
                    
                    # CRITICAL: Final AWS cleanup pass before writing
                    if language == 'python' and hasattr(self.refactoring_service.ast_engine, '_aggressive_aws_cleanup'):
                        refactored_content = self.refactoring_service.ast_engine._aggressive_aws_cleanup(refactored_content)
                    
                    # Write refactored content if changed
                    if refactored_content != original_content:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(refactored_content)
                        files_changed.append(file_path)
                        print(f"✅ Successfully refactored: {file_path}")
                    else:
                        print(f"⚠️  No changes detected for: {file_path} (content unchanged)")
                        # Still count as changed if services were applied (even if content didn't change)
                        if services_applied:
                            files_changed.append(file_path)
                            print(f"✅ Added to changed list (services applied but no content diff)")
                
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    error_msg = f"{str(e)}\n\nTraceback:\n{error_traceback}"
                    print(f"❌ ERROR processing {file_path}: {error_msg}")
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
            
            # Read refactored file contents for display
            # IMPORTANT: Read files IMMEDIATELY after writing them, before any cleanup
            refactored_files_content = {}
            for file_path in files_changed:
                full_path = os.path.join(repository.local_path, file_path)
                print(f"Reading refactored file for display: {file_path} -> {full_path}")
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # CRITICAL: Final AWS cleanup pass on read content before returning
                            if language == 'python' and hasattr(self.refactoring_service.ast_engine, '_aggressive_aws_cleanup'):
                                content = self.refactoring_service.ast_engine._aggressive_aws_cleanup(content)
                            
                            refactored_files_content[file_path] = content
                            print(f"✅ Read {len(content)} characters from {file_path}")
                    except Exception as e:
                        print(f"❌ Warning: Could not read refactored file {file_path}: {e}")
                        import traceback
                        print(f"Traceback: {traceback.format_exc()}")
                        refactored_files_content[file_path] = None
                else:
                    print(f"❌ File does not exist: {full_path}")
                    refactored_files_content[file_path] = None
            
            print(f"Refactored files content keys: {list(refactored_files_content.keys())}")
            for key, value in refactored_files_content.items():
                if value:
                    print(f"  {key}: {len(value)} chars")
                else:
                    print(f"  {key}: None")
            
            result = {
                'success': migration_success and test_success,
                'repository_id': repository_id,
                'files_changed': files_changed,
                'files_failed': files_failed,
                'total_files_changed': len(files_changed),
                'total_files_failed': len(files_failed),
                'refactored_files': refactored_files_content  # Add refactored file contents
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
            import traceback
            error_traceback = traceback.format_exc()
            error_msg = str(e)
            
            print(f"❌ FATAL ERROR in migration: {error_msg}")
            print(f"Traceback: {error_traceback}")
            
            repository = repository.update_status(RepositoryStatus.FAILED)
            repository.metadata['error'] = error_msg
            self.repository_repo.save(repository)
            
            return {
                'success': False,
                'error': error_msg,
                'files_changed': files_changed if 'files_changed' in locals() else [],
                'files_failed': files_failed if 'files_failed' in locals() else [],
                'total_files_changed': len(files_changed) if 'files_changed' in locals() else 0,
                'total_files_failed': len(files_failed) if 'files_failed' in locals() else 0
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
