#!/usr/bin/env python3
"""
Test the standalone transformation function directly
"""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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
print("TESTING STANDALONE TRANSFORMATION FUNCTION")
print("=" * 80)

# Import the standalone function
from application.use_cases import _transform_code_standalone
from domain.entities.codebase import Codebase, ProgrammingLanguage
from datetime import datetime

# Create a codebase (minimal)
codebase = Codebase(
    id="test",
    path="/tmp",
    language=ProgrammingLanguage.PYTHON,
    files=[],
    dependencies={},
    created_at=datetime.now()
)

print("\nCalling _transform_code_standalone...")
print("This function is OUTSIDE the class and should NOT capture any frozen dataclasses")

try:
    result = _transform_code_standalone(
        content=S3_CODE,
        language="python",
        service_type="s3_to_gcs",
        llm_provider=None,  # No LLM
        codebase_obj=codebase,
        file_path="/tmp/test.py"
    )
    
    transformed_content, variable_mapping = result
    
    print("\n" + "=" * 80)
    print("✅ SUCCESS! No FrozenInstanceError!")
    print("=" * 80)
    print(f"\nTransformed {len(transformed_content)} characters")
    print(f"Mapped {len(variable_mapping)} variables")
    
    if "storage" in transformed_content.lower():
        print("\n✅ Transformation successful - found 'storage' in output")
        print("\nFirst 20 lines:")
        for i, line in enumerate(transformed_content.split('\n')[:20], 1):
            print(f"  {i:2}: {line}")
    
    print("\n" + "=" * 80)
    print("✅ TEST PASSED - Standalone function works!")
    print("=" * 80)
    sys.exit(0)
    
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    
    print("\n" + "=" * 80)
    print("❌ TEST FAILED")
    print("=" * 80)
    print(f"\nError Type: {error_type}")
    print(f"Error Message: {error_msg[:400]}")
    
    if "FrozenInstanceError" in error_type or "cannot assign to field" in error_msg.lower():
        print("\n❌ FROZEN DATACLASS ERROR STILL OCCURS!")
        print("Even the standalone function has the issue!")
    else:
        print("\n⚠️  Different error (not frozen dataclass)")
    
    import traceback
    traceback.print_exc()
    sys.exit(1)
