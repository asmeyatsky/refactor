"""
Application Layer - Use Cases

Architectural Intent:
- Contains the use cases that orchestrate the domain layer
- Implements the application-specific business logic
- Acts as a facade between presentation layer and domain layer
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan, RefactoringTask
from domain.services import RefactoringDomainService
from infrastructure.adapters.service_mapping import ExtendedCodeAnalyzer
from domain.ports import (
    CodeAnalyzerPort, LLMProviderPort, ASTTransformationPort,
    TestRunnerPort, FileRepositoryPort, CodebaseRepositoryPort,
    PlanRepositoryPort
)
from domain.value_objects import RefactoringResult, MigrationType


class AnalyzeCodebaseUseCase:
    """Use case for analyzing a codebase to identify refactoring opportunities"""

    def __init__(
        self,
        code_analyzer: CodeAnalyzerPort,
        codebase_repo: CodebaseRepositoryPort
    ):
        self.code_analyzer = code_analyzer
        self.codebase_repo = codebase_repo
        self.extended_analyzer = ExtendedCodeAnalyzer()

    def execute(self, codebase_id: str) -> Dict[str, Any]:
        """Analyze the codebase and return a report of AWS service usage"""
        codebase = self.codebase_repo.load(codebase_id)
        if not codebase:
            raise ValueError(f"Codebase with ID {codebase_id} not found")

        # Use the extended analyzer to identify all cloud service usage (AWS and Azure)
        all_cloud_services = {}
        for file_path in codebase.files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Check for AWS services
                    aws_services_found = self.extended_analyzer.identify_aws_services_usage(content)
                    for service, matches in aws_services_found.items():
                        service_key = f"aws_{service.value}"
                        if service_key not in all_cloud_services:
                            all_cloud_services[service_key] = []
                        all_cloud_services[service_key].extend([file_path] * len(matches))

                    # Check for Azure services
                    azure_services_found = self.extended_analyzer.identify_azure_services_usage(content)
                    for service, matches in azure_services_found.items():
                        service_key = f"azure_{service.value}"
                        if service_key not in all_cloud_services:
                            all_cloud_services[service_key] = []
                        all_cloud_services[service_key].extend([file_path] * len(matches))
            except Exception:
                continue

        dependencies = self.code_analyzer.analyze_dependencies(codebase)

        return {
            "codebase_id": codebase_id,
            "cloud_services_found": all_cloud_services,  # Now includes both AWS and Azure services
            "dependencies": dependencies,
            "language": codebase.language.value,
            "analysis_timestamp": datetime.now().isoformat()
        }


class CreateMultiServiceRefactoringPlanUseCase:
    """Use case for creating a multi-service refactoring plan"""

    def __init__(
        self,
        refactoring_service: RefactoringDomainService,
        plan_repo: PlanRepositoryPort,
        codebase_repo: CodebaseRepositoryPort
    ):
        self.refactoring_service = refactoring_service
        self.plan_repo = plan_repo
        self.codebase_repo = codebase_repo

    def execute(self, codebase_id: str, services_to_migrate: Optional[List[str]] = None) -> RefactoringPlan:
        """Create and save a multi-service refactoring plan for the specified codebase"""
        codebase = self.codebase_repo.load(codebase_id)
        if not codebase:
            raise ValueError(f"Codebase with ID {codebase_id} not found")

        # If services_to_migrate is not specified, we'll create a plan that identifies them automatically
        if services_to_migrate is None:
            # Analyze the codebase to identify which services need migration
            analyze_use_case = AnalyzeCodebaseUseCase(self.refactoring_service.code_analyzer, self.codebase_repo)
            analysis = analyze_use_case.execute(codebase_id)
            # Get all cloud services (both AWS and Azure)
            services_to_migrate = list(analysis['cloud_services_found'].keys())

        # Create tasks for each identified service
        all_tasks = []
        task_id_counter = 0

        for service in services_to_migrate:
            # Get files related to this service
            for file_path in codebase.files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Check if this file contains the service (handle both aws_ and azure_ prefixes)
                        service_lower = service.lower()
                        if service_lower.replace('aws_', '').replace('azure_', '') in content.lower():
                            # Determine if this is AWS or Azure service
                            if service.startswith('aws_'):
                                provider = "AWS"
                                service_name = service.replace('aws_', '').upper()
                            elif service.startswith('azure_'):
                                provider = "Azure"
                                service_name = service.replace('azure_', '').upper().replace('_', ' ')
                            else:
                                provider = "Cloud"
                                service_name = service.upper()

                            task = RefactoringTask(
                                id=f"task_{task_id_counter}_{service}_{file_path.replace('/', '_').replace('.', '_')}",
                                description=f"Refactor {file_path} to replace {provider} {service_name} with GCP equivalent",
                                file_path=file_path,
                                operation=f"migrate_{service.lower()}_to_gcp"
                            )
                            all_tasks.append(task)
                            task_id_counter += 1
                except Exception:
                    continue

        # If no specific service files found, create a general analysis task
        if not all_tasks:
            all_tasks.append(RefactoringTask(
                id="task_general_analysis",
                description="General code analysis - no specific cloud services detected",
                file_path="",
                operation="no_op"
            ))

        plan = RefactoringPlan(
            id=f"plan_{codebase.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            codebase_id=codebase.id,
            tasks=all_tasks,
            created_at=datetime.now(),
            metadata={
                "migration_type": "multi_service_cloud_to_gcp",  # Updated to reflect support for any cloud
                "source_language": codebase.language.value,
                "services_to_migrate": services_to_migrate
            }
        )

        self.plan_repo.save(plan)

        return plan


class ExecuteMultiServiceRefactoringPlanUseCase:
    """Use case for executing a multi-service refactoring plan"""

    def __init__(
        self,
        refactoring_service: RefactoringDomainService,
        plan_repo: PlanRepositoryPort,
        codebase_repo: CodebaseRepositoryPort,
        file_repo: FileRepositoryPort,
        test_runner: TestRunnerPort
    ):
        self.refactoring_service = refactoring_service
        self.plan_repo = plan_repo
        self.codebase_repo = codebase_repo
        self.file_repo = file_repo
        self.test_runner = test_runner

    def execute(self, plan_id: str) -> RefactoringResult:
        """Execute the multi-service refactoring plan and return results"""
        plan = self.plan_repo.load(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")

        codebase = self.codebase_repo.load(plan.codebase_id)
        if not codebase:
            raise ValueError(f"Codebase with ID {plan.codebase_id} not found")

        # Execute each task in the plan
        errors = []
        warnings = []
        transformed_files = 0
        service_results = {}

        for task in plan.get_pending_tasks():
            try:
                # Mark task as in progress
                plan = self.plan_repo.load(plan_id)  # Refresh plan state
                plan = plan.mark_task_in_progress(task.id)
                self.plan_repo.save(plan)

                # Identify service type from operation
                service_type = self._get_service_type_from_operation(task.operation)

                # Execute the refactoring task based on service type
                if task.operation != "no_op":  # Skip no-op tasks
                    transformed_content = self._execute_service_refactoring(codebase, task, service_type)

                    # Write the transformed content back to the file
                    self.file_repo.write_file(task.file_path, transformed_content)
                    transformed_files += 1

                    # Update service results
                    if service_type not in service_results:
                        service_results[service_type] = {'success': 0, 'failed': 0}
                    service_results[service_type]['success'] += 1

                # Mark task as completed
                plan = self.plan_repo.load(plan_id)  # Refresh plan state
                plan = plan.mark_task_completed(task.id)
                self.plan_repo.save(plan)

            except Exception as e:
                # Mark task as failed
                plan = self.plan_repo.load(plan_id)  # Refresh plan state
                plan = plan.mark_task_failed(task.id, str(e))
                self.plan_repo.save(plan)
                errors.append(f"Task {task.id} failed: {str(e)}")

                # Update service results for failure
                service_type = self._get_service_type_from_operation(task.operation)
                if service_type:
                    if service_type not in service_results:
                        service_results[service_type] = {'success': 0, 'failed': 0}
                    service_results[service_type]['failed'] += 1

        # After all tasks are complete, run tests to verify behavior preservation
        test_results = self.test_runner.run_tests(codebase)
        test_success = test_results.get("success", False)

        if not test_success:
            errors.append("Tests failed after refactoring - behavior may not be preserved")

        # Determine overall success
        success = len(errors) == 0 and test_success

        return RefactoringResult(
            success=success,
            message=f"Multi-service refactoring completed with {transformed_files} files transformed",
            transformed_files=transformed_files,
            errors=errors,
            warnings=warnings,
            service_results=service_results
        )

    def _get_service_type_from_operation(self, operation: str) -> str:
        """Extract service type from operation string"""
        if 's3' in operation.lower():
            return 's3_to_gcs'
        elif 'lambda' in operation.lower():
            return 'lambda_to_cloud_functions'
        elif 'dynamodb' in operation.lower():
            return 'dynamodb_to_firestore'
        elif 'sqs' in operation.lower():
            return 'sqs_to_pubsub'
        elif 'sns' in operation.lower():
            return 'sns_to_pubsub'
        elif 'rds' in operation.lower():
            return 'rds_to_cloud_sql'
        elif 'cloudwatch' in operation.lower():
            return 'cloudwatch_to_monitoring'
        elif 'apigateway' in operation.lower():
            return 'apigateway_to_apigee'
        elif 'eks' in operation.lower():
            return 'eks_to_gke'
        elif 'fargate' in operation.lower():
            return 'fargate_to_cloudrun'
        else:
            return 'unknown'

    def _execute_service_refactoring(self, codebase: Codebase, task: RefactoringTask, service_type: str) -> str:
        """Execute refactoring for a specific service type"""
        # This would integrate with the extended semantic engine
        # For now, we'll simulate the refactoring

        with open(task.file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # In a real implementation, this would use the extended semantic engine
        # For simulation, we'll return the content with a service-specific comment
        return f"# REFACTORED: {service_type}\n{original_content}"


class CreateRefactoringPlanUseCase:
    """Use case for creating a refactoring plan"""
    
    def __init__(
        self,
        refactoring_service: RefactoringDomainService,
        plan_repo: PlanRepositoryPort,
        codebase_repo: CodebaseRepositoryPort
    ):
        self.refactoring_service = refactoring_service
        self.plan_repo = plan_repo
        self.codebase_repo = codebase_repo

    def execute(self, codebase_id: str) -> RefactoringPlan:
        """Create and save a refactoring plan for the specified codebase"""
        codebase = self.codebase_repo.load(codebase_id)
        if not codebase:
            raise ValueError(f"Codebase with ID {codebase_id} not found")
        
        plan = self.refactoring_service.create_refactoring_plan(codebase)
        self.plan_repo.save(plan)
        
        return plan


class ExecuteRefactoringPlanUseCase:
    """Use case for executing a refactoring plan"""
    
    def __init__(
        self,
        refactoring_service: RefactoringDomainService,
        plan_repo: PlanRepositoryPort,
        codebase_repo: CodebaseRepositoryPort,
        file_repo: FileRepositoryPort,
        test_runner: TestRunnerPort
    ):
        self.refactoring_service = refactoring_service
        self.plan_repo = plan_repo
        self.codebase_repo = codebase_repo
        self.file_repo = file_repo
        self.test_runner = test_runner

    def execute(self, plan_id: str) -> RefactoringResult:
        """Execute the refactoring plan and return results"""
        plan = self.plan_repo.load(plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        codebase = self.codebase_repo.load(plan.codebase_id)
        if not codebase:
            raise ValueError(f"Codebase with ID {plan.codebase_id} not found")
        
        # Execute each task in the plan
        errors = []
        warnings = []
        transformed_files = 0
        
        for task in plan.get_pending_tasks():
            try:
                # Mark task as in progress
                plan = self.plan_repo.load(plan_id)  # Refresh plan state
                plan = plan.mark_task_in_progress(task.id)
                self.plan_repo.save(plan)
                
                # Execute the refactoring task
                if task.operation != "no_op":  # Skip no-op tasks
                    transformed_content = self.refactoring_service.execute_refactoring_task(codebase, task)
                    
                    # Write the transformed content back to the file
                    self.file_repo.write_file(task.file_path, transformed_content)
                    transformed_files += 1
                
                # Mark task as completed
                plan = self.plan_repo.load(plan_id)  # Refresh plan state
                plan = plan.mark_task_completed(task.id)
                self.plan_repo.save(plan)
                
            except Exception as e:
                # Mark task as failed
                plan = self.plan_repo.load(plan_id)  # Refresh plan state
                plan = plan.mark_task_failed(task.id, str(e))
                self.plan_repo.save(plan)
                errors.append(f"Task {task.id} failed: {str(e)}")
        
        # After all tasks are complete, run tests to verify behavior preservation
        test_results = self.test_runner.run_tests(codebase)
        test_success = test_results.get("success", False)
        
        if not test_success:
            errors.append("Tests failed after refactoring - behavior may not be preserved")
        
        # Determine overall success
        success = len(errors) == 0 and test_success
        
        return RefactoringResult(
            success=success,
            message=f"Refactoring completed with {transformed_files} files transformed",
            transformed_files=transformed_files,
            errors=errors,
            warnings=warnings
        )


class InitializeCodebaseUseCase:
    """Use case for initializing a codebase for refactoring"""
    
    def __init__(
        self,
        codebase_repo: CodebaseRepositoryPort,
        code_analyzer: CodeAnalyzerPort
    ):
        self.codebase_repo = codebase_repo
        self.code_analyzer = code_analyzer

    def execute(self, path: str, language: ProgrammingLanguage) -> Codebase:
        """Initialize a codebase from a directory path"""
        import os
        from uuid import uuid4
        
        if not os.path.exists(path):
            raise ValueError(f"Path {path} does not exist")
        
        # Get all files in the directory (recursively)
        files = []
        for root, dirs, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith(('.py', '.java', '.js', '.ts', '.json', '.yml', '.yaml', '.xml', '.properties')):
                    files.append(os.path.join(root, filename))
        
        # Analyze dependencies
        dependencies = self.code_analyzer.analyze_dependencies(
            Codebase(
                id=str(uuid4()),
                path=path,
                language=language,
                files=files,
                dependencies={},
                created_at=datetime.now()
            )
        )
        
        # Create codebase entity
        codebase = Codebase(
            id=str(uuid4()),
            path=path,
            language=language,
            files=files,
            dependencies=dependencies,
            created_at=datetime.now()
        )
        
        # Save the codebase
        self.codebase_repo.save(codebase)
        
        return codebase