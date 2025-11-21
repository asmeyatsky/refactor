#!/usr/bin/env python3
"""
Test to verify the frozen dataclass fix works correctly
"""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from domain.entities.refactoring_plan import RefactoringTask, TaskStatus
from domain.entities.codebase import Codebase, ProgrammingLanguage
from datetime import datetime
from application.use_cases import ExecuteMultiServiceRefactoringPlanUseCase

# The exact S3 code snippet from the user
S3_CODE_SNIPPET = """import boto3

def create_s3_bucket(bucket_name, region='us-east-1'):
    try:
        s3 = boto3.client('s3', region_name=region)
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        print(f"Bucket '{bucket_name}' created successfully in region '{region}'.")
        return True
    except Exception as e:
        print(f"Error creating bucket '{bucket_name}': {e}")
        return False

def upload_file_to_s3(file_path, bucket_name, object_name=None):
    if object_name is None:
        object_name = file_path.split('/')[-1]
    try:
        s3 = boto3.client('s3')
        s3.upload_file(file_path, bucket_name, object_name)
        print(f"File '{file_path}' uploaded to '{bucket_name}/{object_name}' successfully.")
        return True
    except Exception as e:
        print(f"Error uploading file '{file_path}': {e}")
        return False
"""


def test_frozen_dataclass_fix():
    """Test that _execute_service_refactoring doesn't fail with frozen dataclass error"""
    print("=" * 80)
    print("Testing Frozen Dataclass Fix")
    print("=" * 80)
    
    # Create a temporary directory and file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_s3_code.py"
        temp_file.write_text(S3_CODE_SNIPPET)
        
        print(f"\n1. Created test file: {temp_file}")
        print(f"   File exists: {temp_file.exists()}")
        
        # Create a frozen RefactoringTask (exactly like in production)
        task = RefactoringTask(
            id="test_task_1",
            description="Test S3 to GCS migration",
            file_path=str(temp_file),
            operation="migrate_s3_to_gcp",
            status=TaskStatus.PENDING
        )
        
        print(f"\n2. Created frozen RefactoringTask:")
        print(f"   Task ID: {task.id}")
        print(f"   File path: {task.file_path}")
        print(f"   Task is frozen: {task.__dataclass_params__.frozen if hasattr(task, '__dataclass_params__') else 'unknown'}")
        
        # Verify task is frozen by trying to modify it (should fail)
        try:
            task.id = "modified"  # This should fail
            print(f"   ⚠️  WARNING: Task is NOT frozen!")
        except Exception:
            print(f"   ✅ Task is frozen (cannot modify)")
        
        # Create a Codebase entity
        codebase = Codebase(
            id="test_codebase_1",
            path=str(temp_dir),
            language=ProgrammingLanguage.PYTHON,
            files=[str(temp_file)],
            dependencies={},
            created_at=datetime.now()
        )
        
        print(f"\n3. Created Codebase:")
        print(f"   Language: {codebase.language.value}")
        print(f"   Files: {len(codebase.files)}")
        
        # Create the use case instance
        # We need to mock the dependencies since we're testing in isolation
        try:
            from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
            orchestrator = create_multi_service_migration_system()
            
            print(f"\n4. Created migration orchestrator")
            
            # Create a plan (we'll need to create a minimal plan)
            from domain.entities.refactoring_plan import RefactoringPlan
            from domain.services import RefactoringDomainService
            from infrastructure.repositories import InMemoryPlanRepository, InMemoryCodebaseRepository, InMemoryFileRepository
            from infrastructure.adapters import InMemoryTestRunner
            
            plan_repo = InMemoryPlanRepository()
            codebase_repo = InMemoryCodebaseRepository()
            file_repo = InMemoryFileRepository()
            test_runner = InMemoryTestRunner()
            
            # Save codebase
            codebase_repo.save(codebase)
            
            # Create a plan with our task
            plan = RefactoringPlan(
                id="test_plan_1",
                codebase_id=codebase.id,
                tasks=[task],
                created_at=datetime.now()
            )
            plan_repo.save(plan)
            
            print(f"\n5. Created RefactoringPlan with task")
            
            # Now test the actual method that was failing
            use_case = ExecuteMultiServiceRefactoringPlanUseCase(
                plan_repo=plan_repo,
                codebase_repo=codebase_repo,
                file_repo=file_repo,
                test_runner=test_runner,
                llm_provider=None  # Don't use LLM for this test
            )
            
            print(f"\n6. Created ExecuteMultiServiceRefactoringPlanUseCase")
            print(f"\n7. Testing _execute_service_refactoring method...")
            
            # This is the method that was failing
            try:
                transformed_content, variable_mapping = use_case._execute_service_refactoring(
                    codebase=codebase,
                    task=task,
                    service_type="s3_to_gcs"
                )
                
                print(f"\n✅ SUCCESS! Method executed without frozen dataclass error!")
                print(f"\n   Transformed content length: {len(transformed_content)} characters")
                print(f"   Variable mapping: {variable_mapping}")
                
                # Check that transformation actually happened
                if "boto3" not in transformed_content or "storage.Client()" in transformed_content:
                    print(f"\n✅ Transformation appears successful!")
                    print(f"   Original had boto3: {'boto3' in S3_CODE_SNIPPET}")
                    print(f"   Transformed has storage.Client: {'storage.Client()' in transformed_content}")
                else:
                    print(f"\n⚠️  Transformation may not have worked completely")
                
                return True
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                print(f"\n❌ FAILED! Error occurred:")
                print(f"   Error type: {error_type}")
                print(f"   Error message: {error_msg}")
                
                if "FrozenInstanceError" in error_type or "cannot assign to field" in error_msg:
                    print(f"\n❌ This is the frozen dataclass error we're trying to fix!")
                    import traceback
                    print(f"\nFull traceback:")
                    traceback.print_exc()
                    return False
                else:
                    print(f"\n⚠️  Different error occurred (not the frozen dataclass issue)")
                    import traceback
                    traceback.print_exc()
                    return False
                    
        except ImportError as e:
            print(f"\n⚠️  Could not import required modules: {e}")
            print(f"   This is expected if dependencies are missing")
            print(f"   But the syntax fix should still work")
            return None
        except Exception as e:
            print(f"\n❌ Unexpected error during setup: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("FROZEN DATACLASS FIX TEST")
    print("=" * 80)
    
    result = test_frozen_dataclass_fix()
    
    print("\n" + "=" * 80)
    if result is True:
        print("✅ TEST PASSED - Frozen dataclass fix works!")
    elif result is False:
        print("❌ TEST FAILED - Frozen dataclass error still occurs")
    else:
        print("⚠️  TEST INCONCLUSIVE - Could not run full test")
    print("=" * 80)
    
    sys.exit(0 if result is True else 1)
