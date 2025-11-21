#!/usr/bin/env python3
"""
Direct test of the frozen dataclass fix
Tests the exact method that was failing
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


def test_direct_method_call():
    """Directly test _execute_service_refactoring method"""
    print("=" * 80)
    print("DIRECT TEST: _execute_service_refactoring with frozen dataclass")
    print("=" * 80)
    
    # Create a temporary directory and file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "test_s3_code.py"
        temp_file.write_text(S3_CODE_SNIPPET)
        
        print(f"\n1. Created test file: {temp_file}")
        
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
        
        # Verify task is frozen
        try:
            task.id = "modified"  # This should fail
            print(f"   ❌ ERROR: Task is NOT frozen!")
            return False
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
        
        print(f"\n3. Created Codebase (language: {codebase.language.value})")
        
        # Create the use case instance directly
        try:
            from application.use_cases import ExecuteMultiServiceRefactoringPlanUseCase
            
            # Create use case with None LLM provider (to avoid LLM calls)
            use_case = ExecuteMultiServiceRefactoringPlanUseCase(
                plan_repo=None,  # We won't use it
                codebase_repo=None,
                file_repo=None,
                test_runner=None,
                llm_provider=None  # No LLM for this test
            )
            
            print(f"\n4. Created ExecuteMultiServiceRefactoringPlanUseCase instance")
            print(f"\n5. Calling _execute_service_refactoring method...")
            print(f"   This is the method that was failing with FrozenInstanceError")
            print(f"   Task object will be passed (frozen dataclass)")
            print(f"   Method should extract file_path and delete task reference")
            
            # THIS IS THE EXACT CALL THAT WAS FAILING
            try:
                transformed_content, variable_mapping = use_case._execute_service_refactoring(
                    codebase=codebase,
                    task=task,
                    service_type="s3_to_gcs"
                )
                
                print(f"\n✅ SUCCESS! Method executed without FrozenInstanceError!")
                print(f"\n   Results:")
                print(f"   - Transformed content length: {len(transformed_content)} characters")
                print(f"   - Variable mapping keys: {list(variable_mapping.keys()) if variable_mapping else 'None'}")
                
                # Verify transformation happened
                has_boto3 = "boto3" in transformed_content
                has_storage = "storage.Client()" in transformed_content or "from google.cloud import storage" in transformed_content
                
                print(f"\n   Transformation check:")
                print(f"   - Still has 'boto3': {has_boto3}")
                print(f"   - Has 'storage.Client()' or GCS import: {has_storage}")
                
                if has_storage:
                    print(f"\n✅ Transformation appears successful!")
                    # Show a snippet
                    lines = transformed_content.split('\n')[:10]
                    print(f"\n   First 10 lines of transformed code:")
                    for i, line in enumerate(lines, 1):
                        print(f"   {i:2}: {line}")
                
                return True
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                print(f"\n❌ FAILED! Error occurred:")
                print(f"   Error type: {error_type}")
                print(f"   Error message: {error_msg[:200]}...")
                
                if "FrozenInstanceError" in error_type or "cannot assign to field" in error_msg.lower():
                    print(f"\n❌ THIS IS THE FROZEN DATACLASS ERROR WE'RE TRYING TO FIX!")
                    print(f"\n   The error occurred even though we:")
                    print(f"   1. Extract file_path before transformation")
                    print(f"   2. Delete task reference with 'del task'")
                    print(f"   3. Only use local variables in transformation")
                    
                    import traceback
                    print(f"\n   Full traceback:")
                    traceback.print_exc()
                    return False
                else:
                    print(f"\n⚠️  Different error occurred (not the frozen dataclass issue)")
                    import traceback
                    traceback.print_exc()
                    # Still return False since we want this specific test to pass
                    return False
                    
        except ImportError as e:
            print(f"\n❌ Could not import ExecuteMultiServiceRefactoringPlanUseCase: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DIRECT FROZEN DATACLASS FIX TEST")
    print("=" * 80)
    print("\nThis test directly calls _execute_service_refactoring with a frozen")
    print("RefactoringTask to verify the fix works.\n")
    
    result = test_direct_method_call()
    
    print("\n" + "=" * 80)
    if result is True:
        print("✅ TEST PASSED!")
        print("   The frozen dataclass fix works correctly.")
        print("   _execute_service_refactoring can handle frozen RefactoringTask.")
    else:
        print("❌ TEST FAILED!")
        print("   The frozen dataclass error still occurs.")
        print("   The fix needs further investigation.")
    print("=" * 80)
    
    sys.exit(0 if result is True else 1)
