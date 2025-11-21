#!/usr/bin/env python3
"""
Direct test of _execute_service_refactoring method
"""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from domain.entities.refactoring_plan import RefactoringTask, TaskStatus
from domain.entities.codebase import Codebase, ProgrammingLanguage
from datetime import datetime

S3_CODE = """import boto3

def create_s3_bucket(bucket_name, region='us-east-1'):
    try:
        s3 = boto3.client('s3', region_name=region)
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        return True
    except Exception as e:
        return False
"""

print("=" * 80)
print("DIRECT METHOD TEST")
print("=" * 80)

with tempfile.TemporaryDirectory() as temp_dir:
    temp_file = Path(temp_dir) / "test.py"
    temp_file.write_text(S3_CODE)
    
    # Create frozen task
    task = RefactoringTask(
        id="test",
        description="test",
        file_path=str(temp_file),
        operation="migrate_s3_to_gcp"
    )
    
    # Verify frozen
    try:
        task.id = "modified"
        print("❌ Task not frozen!")
        sys.exit(1)
    except:
        print("✅ Task is frozen")
    
    codebase = Codebase(
        id="test",
        path=str(temp_dir),
        language=ProgrammingLanguage.PYTHON,
        files=[str(temp_file)],
        dependencies={},
        created_at=datetime.now()
    )
    
    # Create a minimal use case instance
    from application.use_cases import ExecuteMultiServiceRefactoringPlanUseCase
    from domain.services import RefactoringDomainService
    from infrastructure.repositories import PlanRepositoryAdapter, CodebaseRepositoryAdapter, FileRepositoryAdapter
    
    # Create minimal test runner
    class MinimalTestRunner:
        def run_tests(self, codebase):
            return {"success": True}
    
    plan_repo = PlanRepositoryAdapter()
    codebase_repo = CodebaseRepositoryAdapter()
    file_repo = FileRepositoryAdapter()
    test_runner = MinimalTestRunner()
    refactoring_service = RefactoringDomainService()
    
    use_case = ExecuteMultiServiceRefactoringPlanUseCase(
        refactoring_service=refactoring_service,
        plan_repo=plan_repo,
        codebase_repo=codebase_repo,
        file_repo=file_repo,
        test_runner=test_runner,
        llm_provider=None
    )
    
    print("\n" + "=" * 80)
    print("TESTING: _execute_service_refactoring with frozen task")
    print("=" * 80)
    print("\nThis is the EXACT method call that was failing.")
    print("The error was: FrozenInstanceError: cannot assign to field 'metadata'")
    print("\nCalling method now...\n")
    
    try:
        result = use_case._execute_service_refactoring(
            codebase=codebase,
            task=task,
            service_type="s3_to_gcs"
        )
        
        transformed_content, variable_mapping = result
        
        print("=" * 80)
        print("✅ SUCCESS! Method executed without FrozenInstanceError!")
        print("=" * 80)
        print(f"\nResults:")
        print(f"  - Transformed content: {len(transformed_content)} characters")
        print(f"  - Variable mappings: {len(variable_mapping)} variables")
        
        # Check transformation
        has_boto3 = "boto3" in transformed_content
        has_storage = "storage" in transformed_content.lower() or "google.cloud" in transformed_content
        
        print(f"\nTransformation check:")
        print(f"  - Still has 'boto3': {has_boto3}")
        print(f"  - Has GCS imports/clients: {has_storage}")
        
        if has_storage:
            print(f"\n✅ Transformation successful!")
            print(f"\nFirst 15 lines of transformed code:")
            for i, line in enumerate(transformed_content.split('\n')[:15], 1):
                print(f"  {i:2}: {line}")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED - Fix works!")
        print("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"\nError Type: {error_type}")
        print(f"Error Message: {error_msg[:400]}")
        
        if "FrozenInstanceError" in error_type or "cannot assign to field" in error_msg.lower():
            print(f"\n❌ THIS IS THE FROZEN DATACLASS ERROR!")
            print(f"\nThe fix did not work. The error still occurs.")
        else:
            print(f"\n⚠️  Different error (not the frozen dataclass issue)")
        
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
        
        sys.exit(1)
