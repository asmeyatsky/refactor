#!/usr/bin/env python3
"""
Final test - directly test the method with the exact scenario
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

def upload_file_to_s3(file_path, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_path.split('/')[-1]
    try:
        s3 = boto3.client('s3')
        s3.upload_file(file_path, bucket_name, object_name)
        return True
    except Exception as e:
        return False
"""

print("=" * 80)
print("FINAL TEST: Frozen Dataclass Fix")
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
    
    # Import and create use case
    from application.use_cases import ExecuteMultiServiceRefactoringPlanUseCase
    from domain.services import RefactoringDomainService
    from infrastructure.repositories import PlanRepositoryAdapter, CodebaseRepositoryAdapter, FileRepositoryAdapter
    from infrastructure.adapters.test_execution_framework import TestExecutionFramework
    
    plan_repo = PlanRepositoryAdapter()
    codebase_repo = CodebaseRepositoryAdapter()
    file_repo = FileRepositoryAdapter()
    test_runner = TestExecutionFramework()
    refactoring_service = RefactoringDomainService()
    
    use_case = ExecuteMultiServiceRefactoringPlanUseCase(
        refactoring_service=refactoring_service,
        plan_repo=plan_repo,
        codebase_repo=codebase_repo,
        file_repo=file_repo,
        test_runner=test_runner,
        llm_provider=None
    )
    
    print("\nCalling _execute_service_refactoring with frozen task...")
    
    try:
        result = use_case._execute_service_refactoring(
            codebase=codebase,
            task=task,
            service_type="s3_to_gcs"
        )
        
        transformed_content, variable_mapping = result
        print(f"\n✅ SUCCESS! No FrozenInstanceError!")
        print(f"   Transformed {len(transformed_content)} chars")
        print(f"   Variables mapped: {len(variable_mapping)}")
        
        if "storage" in transformed_content.lower():
            print(f"✅ Transformation worked!")
        
        print("\n" + "=" * 80)
        print("✅ TEST PASSED!")
        print("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print(f"\n❌ FAILED!")
        print(f"   Type: {error_type}")
        print(f"   Message: {error_msg[:300]}")
        
        if "FrozenInstanceError" in error_type or "cannot assign to field" in error_msg:
            print(f"\n❌ FROZEN DATACLASS ERROR STILL OCCURS!")
            import traceback
            traceback.print_exc()
        else:
            import traceback
            traceback.print_exc()
        
        sys.exit(1)
