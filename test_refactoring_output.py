#!/usr/bin/env python3
"""
Test script to verify refactored code has no AWS/Azure references
"""

import re
import ast
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock config if needed
try:
    from config import config
except ImportError:
    class MockConfig:
        GCP_PROJECT_ID = "test-project"
        GCP_REGION = "us-central1"
    import config as config_module
    config_module.config = MockConfig()

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedASTTransformationEngine

def test_s3_to_gcs():
    """Test S3 to GCS transformation"""
    print("Testing S3 to GCS transformation...")
    
    input_code = """
import boto3

s3_client = boto3.client('s3')

# Upload file to S3
s3_client.upload_file('local_file.txt', 'my-bucket', 'remote_file.txt')

# Download file from S3
s3_client.download_file('my-bucket', 'remote_file.txt', 'downloaded_file.txt')
"""
    
    engine = ExtendedASTTransformationEngine()
    recipe = {
        'operation': 'service_migration',
        'service_type': 's3_to_gcs',
        'language': 'python'
    }
    
    output_code, _ = engine.transform_code(input_code, 'python', recipe)
    
    # Check for AWS/Azure references
    aws_patterns = [r'\bboto3\b', r'\bAWS\b', r'\bS3\b', r'\bs3\b', r'\bAWS_REGION\b', r'\bS3_BUCKET_NAME\b']
    violations = []
    
    for line_num, line in enumerate(output_code.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in aws_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                if not (line.count('"') % 2 == 1 or line.count("'") % 2 == 1):
                    violations.append(f"Line {line_num}: {pattern} in '{line.strip()}'")
    
    if violations:
        print("❌ FAILED: Found AWS references in output:")
        for v in violations:
            print(f"  {v}")
        print("\nOutput code:")
        print(output_code)
        return False
    else:
        print("✅ PASSED: No AWS references found")
        return True

def test_lambda_to_cloud_functions():
    """Test Lambda to Cloud Functions transformation"""
    print("\nTesting Lambda to Cloud Functions transformation...")
    
    input_code = """
import boto3

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    return {'statusCode': 200, 'body': 'Hello'}
"""
    
    engine = ExtendedASTTransformationEngine()
    recipe = {
        'operation': 'service_migration',
        'service_type': 'lambda_to_cloud_functions',
        'language': 'python'
    }
    
    output_code, _ = engine.transform_code(input_code, 'python', recipe)
    
    # Check for AWS/Azure references
    aws_patterns = [r'\bboto3\b', r'\bAWS\b', r'\bLambda\b', r'\blambda\b', r'\bAWS_LAMBDA\b']
    violations = []
    
    for line_num, line in enumerate(output_code.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in aws_patterns:
            # Skip Python's lambda keyword
            if pattern == r'\blambda\b' and re.search(r'\blambda\s*[:=]', line):
                continue
            if re.search(pattern, line, re.IGNORECASE):
                if not (line.count('"') % 2 == 1 or line.count("'") % 2 == 1):
                    violations.append(f"Line {line_num}: {pattern} in '{line.strip()}'")
    
    if violations:
        print("❌ FAILED: Found AWS references in output:")
        for v in violations:
            print(f"  {v}")
        print("\nOutput code:")
        print(output_code)
        return False
    else:
        print("✅ PASSED: No AWS references found")
        return True

def test_azure_blob_to_gcs():
    """Test Azure Blob Storage to GCS transformation"""
    print("\nTesting Azure Blob Storage to GCS transformation...")
    
    input_code = """
from azure.storage.blob import BlobServiceClient

blob_service_client = BlobServiceClient(
    account_url="https://myaccount.blob.core.windows.net",
    credential="my_account_key"
)

container_client = blob_service_client.get_container_client("mycontainer")
"""
    
    engine = AzureExtendedASTTransformationEngine()
    recipe = {
        'operation': 'service_migration',
        'service_type': 'azure_blob_storage_to_gcs',
        'language': 'python'
    }
    
    output_code = engine.transform_code(input_code, 'python', recipe)
    
    # Check for Azure references
    azure_patterns = [r'\bAzure\b', r'\bazure\b', r'\bBlobServiceClient\b', r'\bAZURE_\b']
    violations = []
    
    for line_num, line in enumerate(output_code.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        for pattern in azure_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                if not (line.count('"') % 2 == 1 or line.count("'") % 2 == 1):
                    violations.append(f"Line {line_num}: {pattern} in '{line.strip()}'")
    
    if violations:
        print("❌ FAILED: Found Azure references in output:")
        for v in violations:
            print(f"  {v}")
        print("\nOutput code:")
        print(output_code)
        return False
    else:
        print("✅ PASSED: No Azure references found")
        return True

def test_syntax_validity():
    """Test that output code is syntactically valid"""
    print("\nTesting syntax validity...")
    
    input_code = """
import boto3
s3 = boto3.client('s3')
s3.upload_file('file.txt', 'bucket', 'key.txt')
"""
    
    engine = ExtendedASTTransformationEngine()
    recipe = {
        'operation': 'service_migration',
        'service_type': 's3_to_gcs',
        'language': 'python'
    }
    
    try:
        output_code, _ = engine.transform_code(input_code, 'python', recipe)
        # Try to parse the output
        ast.parse(output_code)
        print("✅ PASSED: Output code is syntactically valid")
        return True
    except SyntaxError as e:
        print(f"❌ FAILED: Output code has syntax errors: {e}")
        print("\nOutput code:")
        print(output_code)
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Refactoring Output Validation Tests")
    print("=" * 60)
    
    results = []
    results.append(test_s3_to_gcs())
    results.append(test_lambda_to_cloud_functions())
    results.append(test_azure_blob_to_gcs())
    results.append(test_syntax_validity())
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    exit(0 if all(results) else 1)
