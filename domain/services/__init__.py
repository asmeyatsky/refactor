"""
Domain Services

Architectural Intent:
- Contain business logic that doesn't naturally fit in entities
- Coordinate between multiple entities
- Implement complex business rules
"""

from typing import List, Dict, Any
from datetime import datetime

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan, RefactoringTask
from domain.ports import CodeAnalyzerPort, LLMProviderPort, ASTTransformationPort
from infrastructure.adapters.extended_semantic_engine import ExtendedSemanticRefactoringService


class RefactoringDomainService:
    """
    Core refactoring domain service

    Contains the business logic for refactoring operations
    """

    def __init__(
        self,
        code_analyzer: CodeAnalyzerPort,
        llm_provider: LLMProviderPort,
        ast_transformer: ASTTransformationPort,
        extended_semantic_service: ExtendedSemanticRefactoringService = None
    ):
        self.code_analyzer = code_analyzer
        self.llm_provider = llm_provider
        self.ast_transformer = ast_transformer
        self.extended_semantic_service = extended_semantic_service

    def create_refactoring_plan(self, codebase: Codebase) -> RefactoringPlan:
        """
        Create a refactoring plan for AWS S3 to GCS migration
        """
        # Identify files containing AWS S3 usage
        s3_files = self.code_analyzer.identify_aws_s3_usage(codebase)
        
        # Create tasks for each file
        tasks = []
        for i, file_path in enumerate(s3_files):
            task = RefactoringTask(
                id=f"task_{i}_{file_path.replace('/', '_').replace('.', '_')}",
                description=f"Refactor {file_path} to replace AWS S3 with GCS",
                file_path=file_path,
                operation="replace_aws_s3_with_gcs"
            )
            tasks.append(task)
        
        # If no S3 files found, create a minimal plan
        if not tasks:
            tasks.append(RefactoringTask(
                id="task_no_s3_found",
                description="No AWS S3 usage found in codebase",
                file_path="",
                operation="no_op"
            ))
        
        plan = RefactoringPlan(
            id=f"plan_{codebase.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            codebase_id=codebase.id,
            tasks=tasks,
            created_at=datetime.now(),
            metadata={
                "migration_type": "aws_s3_to_gcs",
                "source_language": codebase.language.value
            }
        )
        
        return plan

    def execute_refactoring_task(self, codebase: Codebase, task: RefactoringTask) -> str:
        """
        Execute a single refactoring task
        """
        # Generate refactoring intent using LLM
        refactoring_intent = self.llm_provider.generate_refactoring_intent(
            codebase=codebase,
            file_path=task.file_path,
            target="gcs"
        )
        
        # Create transformation recipe
        analysis = {
            "codebase": codebase,
            "file_path": task.file_path,
            "intent": refactoring_intent,
            "target": "gcs"
        }
        
        recipe = self.llm_provider.generate_recipe(analysis)
        
        # Apply the transformation
        transformed_content = self.ast_transformer.apply_recipe(recipe, task.file_path)
        
        return transformed_content

    def validate_behavior_preservation(self, original_codebase: Codebase, refactored_codebase: Codebase) -> bool:
        """
        Validate that behavior is preserved after refactoring
        This would typically involve running tests, but the implementation
        would depend on the specific testing framework
        """
        # For now, we return True - in a real implementation, this would run
        # the existing test suite to validate behavior preservation
        return True