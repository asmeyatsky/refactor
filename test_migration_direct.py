"""
Direct test of migration functions without API server
Tests the core migration logic directly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine

# Test cases
TEST_CASES = {
    "dynamodb_migration_script": {
        "code": """import boto3
import firebase_admin
from firebase_admin import credentials, firestore
from decimal import Decimal

# Initialize DynamoDB (source)
dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
source_table = dynamodb_resource.Table('SourceDynamoTable')

# Scan DynamoDB table
response = source_table.scan()
items = response.get('Items', [])

# Write to Firestore
for item in items:
    doc_ref = firestore_db.collection('DestinationCollection').document()
    doc_ref.set(item)
""",
        "services": ["dynamodb"],
        "should_preserve_boto3": True
    },
    
    "dynamodb_application_code": {
        "code": """import boto3
import os

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME', 'my-table'))

# Put item
table.put_item(
    Item={
        'id': '123',
        'name': 'Test Item',
        'value': 42
    }
)

# Get item
response = table.get_item(Key={'id': '123'})
item = response.get('Item')
""",
        "services": ["dynamodb"],
        "should_preserve_boto3": False
    },
    
    "s3_basic": {
        "code": """import boto3
import os

s3_client = boto3.client('s3', region_name='us-east-1')
bucket_name = os.getenv('S3_BUCKET_NAME', 'my-bucket')

# Upload file
s3_client.upload_file('local_file.txt', bucket_name, 'remote_file.txt')

# Download file
s3_client.download_file(bucket_name, 'remote_file.txt', 'local_file.txt')
""",
        "services": ["s3"],
        "should_preserve_boto3": False
    },
    
    "lambda_handler": {
        "code": """import json
import boto3

def lambda_handler(event, context):
    # Process S3 event
    for record in event.get('Records', []):
        if record.get('eventSource') == 'aws:s3':
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            print(f"Processing {key} from {bucket}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Success'})
    }
""",
        "services": ["lambda"],
        "should_preserve_boto3": False
    },
    
    "multi_service": {
        "code": """import boto3
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# S3 operation
s3_client.upload_file('file.txt', os.getenv('S3_BUCKET_NAME'), 'file.txt')

# DynamoDB operation
table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
table.put_item(Item={'id': '1', 'name': 'test'})

# SQS operation
sqs.send_message(QueueUrl=os.getenv('SQS_QUEUE_URL'), MessageBody='test')
""",
        "services": ["s3", "dynamodb", "sqs"],
        "should_preserve_boto3": False
    }
}


def test_migration(test_name: str, test_case: dict):
    """Test migration directly"""
    print(f"\n{'='*70}")
    print(f"Testing: {test_name}")
    print(f"{'='*70}")
    
    code = test_case["code"]
    services = test_case["services"]
    should_preserve_boto3 = test_case.get("should_preserve_boto3", False)
    
    print(f"Services: {services}")
    print(f"Should preserve boto3: {should_preserve_boto3}")
    
    try:
        engine = ExtendedASTTransformationEngine()
        
        # Determine service type
        if "dynamodb" in services:
            service_type = "dynamodb_to_firestore"
        elif "s3" in services:
            service_type = "s3_to_gcs"
        elif "lambda" in services:
            service_type = "lambda_to_cloud_functions"
        elif "sqs" in services:
            service_type = "sqs_to_pubsub"
        else:
            service_type = "multi_service"
        
        # Migrate
        result_code, variable_mapping = engine.transform_code(code, "python", {
            "operation": "service_migration",
            "service_type": service_type,
            "services": services
        })
        
        print(f"\nOriginal code length: {len(code)}")
        print(f"Refactored code length: {len(result_code)}")
        
        # Check results
        has_boto3 = "boto3" in result_code.lower()
        has_firestore = "firestore" in result_code.lower() or "google.cloud" in result_code.lower()
        has_gcs = "google.cloud.storage" in result_code.lower() or "storage.Client" in result_code.lower()
        
        print(f"\nResults:")
        print(f"  Contains boto3: {has_boto3}")
        print(f"  Contains Firestore/GCP: {has_firestore or has_gcs}")
        
        # Validation
        if should_preserve_boto3:
            if not has_boto3:
                print(f"  ✗ ERROR: Should preserve boto3 but it's missing!")
                return False
            if not has_firestore:
                print(f"  ✗ ERROR: Should have Firestore but it's missing!")
                return False
            print(f"  ✓ Correctly preserved boto3 for migration script")
        else:
            if has_boto3:
                print(f"  ⚠ WARNING: Found boto3 in refactored code (should be removed)")
                # Check if it's in comments
                if "#" not in result_code.split("boto3")[0][-50:]:
                    print(f"  ✗ ERROR: boto3 found in non-comment code!")
                    return False
            if not (has_firestore or has_gcs):
                print(f"  ✗ ERROR: Missing GCP imports!")
                return False
            print(f"  ✓ Correctly migrated to GCP")
        
        print(f"\n✓ Test passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("="*70)
    print("DIRECT MIGRATION FUNCTION TEST SUITE")
    print("="*70)
    
    results = []
    for test_name, test_case in TEST_CASES.items():
        success = test_migration(test_name, test_case)
        results.append({
            "test_name": test_name,
            "success": success
        })
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["success"]:
                print(f"  ✗ {r['test_name']}")
    
    return all(r["success"] for r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
