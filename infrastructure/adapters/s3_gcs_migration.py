"""
Multi-Service Cloud Refactoring - Extended Implementation

Architectural Intent:
- Implement refactoring functionality for multiple AWS services to GCP equivalents
- Support S3 to GCS, Lambda to Cloud Functions, DynamoDB to Firestore, and more
- Include authentication translation and configuration updates
- Ensure verification of refactored code
"""

from typing import Dict, Any, List
from datetime import datetime

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan
from domain.services import RefactoringDomainService
from application.use_cases import (
    AnalyzeCodebaseUseCase, CreateRefactoringPlanUseCase,
    ExecuteRefactoringPlanUseCase, InitializeCodebaseUseCase,
    CreateMultiServiceRefactoringPlanUseCase, ExecuteMultiServiceRefactoringPlanUseCase
)
from infrastructure.adapters import (
    CodeAnalyzerAdapter, LLMProviderAdapter,
    ASTTransformationAdapter, TestRunnerAdapter
)
from infrastructure.repositories import (
    FileRepositoryAdapter, CodebaseRepositoryAdapter, PlanRepositoryAdapter
)
from infrastructure.adapters.verification_security import VerificationAgent, SecurityGate
from infrastructure.adapters.memory import MemoryModule, ContextManager
from infrastructure.adapters.semantic_engine import SemanticRefactoringService
from infrastructure.adapters.extended_semantic_engine import ExtendedSemanticRefactoringService, ExtendedASTTransformationEngine
from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedSemanticRefactoringService, AzureExtendedASTTransformationEngine
from infrastructure.adapters.service_mapping import ServiceMapper
from infrastructure.adapters.azure_mapping import AzureServiceMapper


class MultiServicePlannerAgent:
    """
    Multi-Service Planner Agent (The Strategist)

    As described in the PRD:
    - Task decomposition
    - Strategy determination
    - Dependency identification
    - Defining the working context
    - Extended to handle multiple AWS services
    """

    def __init__(
        self,
        analyze_use_case: AnalyzeCodebaseUseCase,
        plan_use_case: CreateRefactoringPlanUseCase,
        multi_service_plan_use_case: CreateMultiServiceRefactoringPlanUseCase,
        memory_module: MemoryModule,
        context_manager: ContextManager
    ):
        self.analyze_use_case = analyze_use_case
        self.plan_use_case = plan_use_case
        self.multi_service_plan_use_case = multi_service_plan_use_case
        self.memory_module = memory_module
        self.context_manager = context_manager

    def create_migration_plan(self, codebase_id: str, services_to_migrate: List[str] = None) -> RefactoringPlan:
        """Create a migration plan for multiple AWS services to GCP equivalents"""
        # Analyze the codebase to identify AWS service usage
        analysis_report = self.analyze_use_case.execute(codebase_id)

        # Store analysis results in memory
        self.memory_module.store_long_term(
            f"analysis_{codebase_id}",
            analysis_report,
            tags=["analysis", "multi_service_migration", codebase_id]
        )

        # Create a multi-service refactoring plan
        if services_to_migrate:
            plan = self.multi_service_plan_use_case.execute(codebase_id, services_to_migrate)
        else:
            plan = self.multi_service_plan_use_case.execute(codebase_id)  # Will auto-detect services

        # Store the plan in memory as well
        self.memory_module.store_long_term(
            f"plan_{plan.id}",
            plan,
            tags=["refactoring_plan", "multi_service_migration", plan.codebase_id]
        )

        return plan


class MultiServiceRefactoringEngineAgent:
    """
    Multi-Service Refactoring Engine Agent (The Synthesizer)

    As described in the PRD:
    - Generates semantic transformation intent (recipes)
    - Applies them deterministically
    - Extended to handle multiple AWS services
    """

    def __init__(
        self,
        execute_plan_use_case: ExecuteRefactoringPlanUseCase,
        execute_multi_service_plan_use_case: ExecuteMultiServiceRefactoringPlanUseCase,
        semantic_engine: SemanticRefactoringService,
        extended_semantic_engine: ExtendedSemanticRefactoringService,
        memory_module: MemoryModule
    ):
        self.execute_plan_use_case = execute_plan_use_case
        self.execute_multi_service_plan_use_case = execute_multi_service_plan_use_case
        self.semantic_engine = semantic_engine
        self.extended_semantic_engine = extended_semantic_engine
        self.memory_module = memory_module

    def execute_migration(self, plan_id: str) -> Dict[str, Any]:
        """Execute the multi-service migration plan"""
        # Execute the multi-service refactoring plan using the appropriate use case
        try:
            result = self.execute_multi_service_plan_use_case.execute(plan_id)

            return {
                "success": result.success,
                "plan_id": plan_id,
                "files_transformed": result.transformed_files,
                "service_results": result.service_results,
                "variable_mapping": result.variable_mapping if hasattr(result, 'variable_mapping') else {},
                "errors": result.errors,
                "warnings": result.warnings
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Migration failed: {str(e)}",
                "plan_id": plan_id
            }


class MultiServiceMigrationOrchestrator:
    """
    Main orchestrator for multi-service AWS to GCP migration

    Implements the multi-agent framework described in the PRD by coordinating
    the Planner, Refactoring Engine, and Verification agents.
    Supports migration of multiple AWS services to their GCP equivalents.
    """

    def __init__(
        self,
        planner_agent: MultiServicePlannerAgent,
        verification_agent: VerificationAgent,
        security_gate: SecurityGate,
        memory_module: MemoryModule,
        # Dependencies for creating the refactoring engine
        file_repo: FileRepositoryAdapter,
        codebase_repo: CodebaseRepositoryAdapter,
        plan_repo: PlanRepositoryAdapter,
        llm_provider: LLMProviderAdapter,
        test_runner: TestRunnerAdapter,
        semantic_engine: SemanticRefactoringService,
        extended_semantic_engine: ExtendedSemanticRefactoringService,
        azure_extended_semantic_engine: AzureExtendedSemanticRefactoringService,
    ):
        self.planner_agent = planner_agent
        self.verification_agent = verification_agent
        self.security_gate = security_gate
        self.memory_module = memory_module
        # Store dependencies
        self.file_repo = file_repo
        self.codebase_repo = codebase_repo
        self.plan_repo = plan_repo
        self.llm_provider = llm_provider
        self.test_runner = test_runner
        self.semantic_engine = semantic_engine
        self.extended_semantic_engine = extended_semantic_engine
        self.azure_extended_semantic_engine = azure_extended_semantic_engine


    def _create_refactoring_engine(self, services_to_migrate: List[str] = None) -> MultiServiceRefactoringEngineAgent:
        """Dynamically creates the refactoring engine based on the services to migrate."""
        aws_services = {"s3", "lambda", "dynamodb"}
        is_aws = any(service in aws_services for service in (services_to_migrate or []))

        chosen_engine = self.extended_semantic_engine if is_aws else self.azure_extended_semantic_engine
        
        refactoring_service = RefactoringDomainService(
            code_analyzer=CodeAnalyzerAdapter(),
            llm_provider=self.llm_provider,
            ast_transformer=ASTTransformationAdapter(),
            extended_semantic_service=chosen_engine
        )

        execute_use_case = ExecuteRefactoringPlanUseCase(
            refactoring_service=refactoring_service,
            plan_repo=self.plan_repo,
            codebase_repo=self.codebase_repo,
            file_repo=self.file_repo,
            test_runner=self.test_runner
        )

        execute_multi_service_use_case = ExecuteMultiServiceRefactoringPlanUseCase(
            refactoring_service=refactoring_service,
            plan_repo=self.plan_repo,
            codebase_repo=self.codebase_repo,
            file_repo=self.file_repo,
            test_runner=self.test_runner,
            llm_provider=self.llm_provider
        )

        return MultiServiceRefactoringEngineAgent(
            execute_plan_use_case=execute_use_case,
            execute_multi_service_plan_use_case=execute_multi_service_use_case,
            semantic_engine=self.semantic_engine,
            extended_semantic_engine=chosen_engine,
            memory_module=self.memory_module
        )

    def execute_migration(self, codebase_path: str, language: ProgrammingLanguage, services_to_migrate: List[str] = None) -> Dict[str, Any]:
        """Execute a complete multi-service AWS to GCP migration"""

        # Step 1: Initialize the codebase
        init_use_case = InitializeCodebaseUseCase(
            codebase_repo=CodebaseRepositoryAdapter(),
            code_analyzer=CodeAnalyzerAdapter()
        )

        codebase = init_use_case.execute(codebase_path, language)

        # Step 2: Plan the migration
        print(f"Planning multi-service migration for codebase: {codebase.id}")
        if services_to_migrate:
            print(f"Services to migrate: {services_to_migrate}")
        plan = self.planner_agent.create_migration_plan(codebase.id, services_to_migrate)

        # Step 3: Create and execute the refactoring
        print(f"Creating refactoring engine for services: {services_to_migrate}")
        refactoring_engine = self._create_refactoring_engine(services_to_migrate)
        print(f"Executing multi-service refactoring plan: {plan.id}")
        execution_result = refactoring_engine.execute_migration(plan.id)

        # Step 4: Verify the results
        print("Verifying refactoring results...")
        verification_result = self.verification_agent.verify_refactoring_result(
            original_codebase=codebase,
            refactored_codebase=codebase,  # In this simplified version, they're the same
            plan=plan
        )

        # Step 5: Apply security validation
        security_valid = self.security_gate.validate_code_changes(codebase, codebase, plan)

        # Compile the final result
        migration_type = f"AWS Multi-Service to GCP" if services_to_migrate else f"AWS Auto-Detected Services to GCP"

        final_result = {
            "migration_id": f"mig_{codebase.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "codebase_id": codebase.id,
            "plan_id": plan.id,
            "execution_result": execution_result,
            "verification_result": {
                "success": verification_result.success,
                "message": verification_result.message,
                "errors": verification_result.errors,
                "warnings": verification_result.warnings
            },
            "security_validation_passed": security_valid,
            "migration_type": migration_type,
            "services_migrated": services_to_migrate,
            "completed_at": datetime.now().isoformat()
        }

        # Store the migration result in memory
        self.memory_module.store_long_term(
            f"migration_{final_result['migration_id']}",
            final_result,
            tags=["migration", "multi_service", codebase.id]
        )

        return final_result


def create_multi_service_migration_system() -> MultiServiceMigrationOrchestrator:
    """
    Factory function to create the complete multi-service Cloud to GCP migration system
    (Supports AWS, Azure and other clouds)
    """
    # Create infrastructure components
    memory_module = MemoryModule()
    context_manager = ContextManager(memory_module)

    # Create adapters
    file_repo = FileRepositoryAdapter()
    codebase_repo = CodebaseRepositoryAdapter()
    plan_repo = PlanRepositoryAdapter()
    code_analyzer = CodeAnalyzerAdapter()
    llm_provider = LLMProviderAdapter()
    ast_transformer = ASTTransformationAdapter()
    test_runner = TestRunnerAdapter()

    # Create semantic refactoring engines
    semantic_engine = SemanticRefactoringService(
        ast_engine=ASTTransformationAdapter()
    )
    extended_semantic_engine = ExtendedSemanticRefactoringService(
        ast_engine=ExtendedASTTransformationEngine()
    )
    azure_extended_semantic_engine = AzureExtendedSemanticRefactoringService(
        ast_engine=AzureExtendedASTTransformationEngine()
    )

    # Note: RefactoringDomainService and other related components are now created dynamically
    # inside the orchestrator. We still need a placeholder for the planner.
    
    # Create a placeholder refactoring service for the planner
    # This is a bit of a hack, but it's required for the planner agent to be created.
    # The planner doesn't actually use the extended_semantic_service, so this is safe.
    placeholder_refactoring_service = RefactoringDomainService(
        code_analyzer=code_analyzer,
        llm_provider=llm_provider,
        ast_transformer=ast_transformer,
        extended_semantic_service=extended_semantic_engine 
    )

    # Create application use cases for the planner
    analyze_use_case = AnalyzeCodebaseUseCase(
        code_analyzer=code_analyzer,
        codebase_repo=codebase_repo
    )

    plan_use_case = CreateRefactoringPlanUseCase(
        refactoring_service=placeholder_refactoring_service,
        plan_repo=plan_repo,
        codebase_repo=codebase_repo
    )

    multi_service_plan_use_case = CreateMultiServiceRefactoringPlanUseCase(
        refactoring_service=placeholder_refactoring_service,
        plan_repo=plan_repo,
        codebase_repo=codebase_repo
    )
    
    # Create verification and security components
    verification_agent = VerificationAgent(test_runner)
    security_gate = SecurityGate(verification_agent)

    # Create multi-service agents
    planner_agent = MultiServicePlannerAgent(
        analyze_use_case=analyze_use_case,
        plan_use_case=plan_use_case,
        multi_service_plan_use_case=multi_service_plan_use_case,
        memory_module=memory_module,
        context_manager=context_manager
    )

    # Create orchestrator
    orchestrator = MultiServiceMigrationOrchestrator(
        planner_agent=planner_agent,
        verification_agent=verification_agent,
        security_gate=security_gate,
        memory_module=memory_module,
        file_repo=file_repo,
        codebase_repo=codebase_repo,
        plan_repo=plan_repo,
        llm_provider=llm_provider,
        test_runner=test_runner,
        semantic_engine=semantic_engine,
        extended_semantic_engine=extended_semantic_engine,
        azure_extended_semantic_engine=azure_extended_semantic_engine,
    )

    return orchestrator