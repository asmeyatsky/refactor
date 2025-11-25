"""
Comprehensive test suite for code snippet refactoring
Tests all use cases and validates correctness
"""

import requests
import time
import json
from typing import Dict, Any, List
import sys

BASE_URL = "http://localhost:8000"

# Test cases for different AWS services
AWS_TEST_CASES = {
    "s3": {
        "code": """
import boto3
import os

s3_client = boto3.client('s3', region_name='us-east-1')
bucket_name = os.getenv('S3_BUCKET_NAME', 'my-bucket')

# Upload file
s3_client.upload_file('local_file.txt', bucket_name, 'remote_file.txt')

# Download file
s3_client.download_file(bucket_name, 'remote_file.txt', 'local_file.txt')

# List objects
response = s3_client.list_objects_v2(Bucket=bucket_name)
for obj in response.get('Contents', []):
    print(f"Key: {obj['Key']}")
""",
        "services": ["s3"],
        "expected_gcp_patterns": ["from google.cloud", "storage.Client", "GCS_BUCKET_NAME"],
        "should_not_contain": ["boto3", "s3_client", "S3_BUCKET_NAME"]
    },
    "lambda": {
        "code": """
import json
import boto3

def lambda_handler(event, context):
    # Process S3 event
    for record in event['Records']:
        if record['eventSource'] == 'aws:s3':
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            print(f"Processing {key} from {bucket}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
""",
        "services": ["lambda"],
        "expected_gcp_patterns": ["from google.cloud", "def process"],
        "should_not_contain": ["lambda_handler", "event['Records']"]
    },
    "dynamodb": {
        "code": """
import boto3
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
        "expected_gcp_patterns": ["from google.cloud", "firestore.Client"],
        "should_not_contain": ["boto3", "dynamodb", "DYNAMODB_TABLE_NAME"]
    },
    "sqs": {
        "code": """
import boto3
import os
import json

sqs = boto3.client('sqs', region_name='us-east-1')
queue_url = os.getenv('SQS_QUEUE_URL', 'https://sqs.us-east-1.amazonaws.com/123456789/my-queue')

# Send message
response = sqs.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps({'key': 'value'})
)

# Receive messages
messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
for msg in messages.get('Messages', []):
    print(msg['Body'])
""",
        "services": ["sqs"],
        "expected_gcp_patterns": ["from google.cloud", "pubsub"],
        "should_not_contain": ["boto3", "sqs", "SQS_QUEUE_URL"]
    },
    "sns": {
        "code": """
import boto3
import os
import json

sns = boto3.client('sns', region_name='us-east-1')
topic_arn = os.getenv('SNS_TOPIC_ARN', 'arn:aws:sns:us-east-1:123456789:my-topic')

# Publish message
response = sns.publish(
    TopicArn=topic_arn,
    Message=json.dumps({'key': 'value'}),
    Subject='Test Subject'
)
""",
        "services": ["sns"],
        "expected_gcp_patterns": ["from google.cloud", "pubsub"],
        "should_not_contain": ["boto3", "sns", "SNS_TOPIC_ARN"]
    },
    "multi_service": {
        "code": """
import boto3
import os

# S3 operations
s3 = boto3.client('s3')
s3.upload_file('file.txt', os.getenv('S3_BUCKET_NAME'), 'file.txt')

# DynamoDB operations
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
table.put_item(Item={'id': '1', 'name': 'test'})
""",
        "services": ["s3", "dynamodb"],
        "expected_gcp_patterns": ["google.cloud.storage", "google.cloud.firestore"],
        "should_not_contain": ["boto3", "s3", "dynamodb"]
    }
}

# Test cases for Azure services
AZURE_TEST_CASES = {
    "blob_storage": {
        "code": """
from azure.storage.blob import BlobServiceClient
import os

connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'my-container')

# Upload blob
blob_client = blob_service_client.get_blob_client(container=container_name, blob='my-blob.txt')
with open('local_file.txt', 'rb') as data:
    blob_client.upload_blob(data)

# Download blob
with open('downloaded_file.txt', 'wb') as download_file:
    download_file.write(blob_client.download_blob().readall())
""",
        "services": ["blob_storage"],
        "expected_gcp_patterns": ["from google.cloud", "storage.Client"],
        "should_not_contain": ["azure.storage", "BlobServiceClient", "AZURE_STORAGE"]
    },
    "functions": {
        "code": """
import azure.functions as func
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    name = req.params.get('name')
    return func.HttpResponse(f"Hello {name}!")
""",
        "services": ["functions"],
        "expected_gcp_patterns": ["from google.cloud", "def process"],
        "should_not_contain": ["azure.functions", "func.HttpRequest"]
    },
    "cosmos_db": {
        "code": """
from azure.cosmos import CosmosClient, PartitionKey
import os

endpoint = os.getenv('AZURE_COSMOS_ENDPOINT')
key = os.getenv('AZURE_COSMOS_KEY')
client = CosmosClient(endpoint, key)

database = client.create_database_if_not_exists(id='my-database')
container = database.create_container_if_not_exists(
    id='my-container',
    partition_key=PartitionKey(path='/id')
)

# Create item
container.create_item({'id': '1', 'name': 'test'})
""",
        "services": ["cosmos_db"],
        "expected_gcp_patterns": ["from google.cloud"],
        "should_not_contain": ["azure.cosmos", "CosmosClient", "AZURE_COSMOS"]
    },
    "service_bus": {
        "code": """
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os

connection_string = os.getenv('AZURE_SERVICE_BUS_CONNECTION_STRING')
queue_name = os.getenv('AZURE_SERVICE_BUS_QUEUE_NAME', 'my-queue')

with ServiceBusClient.from_connection_string(connection_string) as client:
    with client.get_queue_sender(queue_name) as sender:
        message = ServiceBusMessage('Hello World')
        sender.send_messages(message)
""",
        "services": ["service_bus"],
        "expected_gcp_patterns": ["google.cloud.pubsub"],
        "should_not_contain": ["azure.servicebus", "ServiceBusClient", "AZURE_SERVICE_BUS"]
    }
}

# Edge cases
EDGE_CASES = {
    "empty_code": {
        "code": "",
        "services": ["s3"],
        "should_fail": False  # Empty code should be handled gracefully
    },
    "invalid_syntax": {
        "code": "def broken_function(:\n    pass",
        "services": ["s3"],
        "should_fail": True  # Should detect syntax errors
    },
    "no_cloud_code": {
        "code": """
def hello_world():
    print("Hello, World!")
    return 42
""",
        "services": ["s3"],
        "should_fail": False  # Code without cloud services should still process
    },
    "java_code": {
        "code": """
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;

public class S3Example {
    public void uploadFile() {
        AmazonS3 s3Client = AmazonS3ClientBuilder.standard().build();
        s3Client.putObject("my-bucket", "key", new File("file.txt"));
    }
}
""",
        "services": ["s3"],
        "language": "java",
        "should_fail": False
    }
}


def test_migration(test_name: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single migration case"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}")
    
    language = test_case.get("language", "python")
    services = test_case.get("services", [])
    code = test_case.get("code", "")
    
    # Submit migration request
    print(f"Submitting migration request...")
    response = requests.post(
        f"{BASE_URL}/api/migrate",
        json={
            "code": code,
            "language": language,
            "services": services
        },
        timeout=30
    )
    
    if response.status_code != 200:
        return {
            "test_name": test_name,
            "success": False,
            "error": f"Failed to submit migration: {response.status_code} - {response.text}"
        }
    
    migration_id = response.json()["migration_id"]
    print(f"Migration ID: {migration_id}")
    
    # Poll for completion
    max_wait = 120  # 2 minutes max
    start_time = time.time()
    last_progress = {"refactoring": 0.0, "validation": 0.0}
    
    while time.time() - start_time < max_wait:
        status_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}")
        if status_response.status_code != 200:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"Failed to get status: {status_response.status_code}"
            }
        
        status_data = status_response.json()
        status = status_data.get("status")
        
        # Show progress updates
        progress = status_data.get("progress", {})
        refactoring_progress = progress.get("refactoring", {}).get("progress", 0.0)
        validation_progress = progress.get("validation", {}).get("progress", 0.0)
        
        if refactoring_progress != last_progress["refactoring"]:
            ref_msg = progress.get("refactoring", {}).get("message", "")
            print(f"  Refactoring: {refactoring_progress:.1f}% - {ref_msg}")
            last_progress["refactoring"] = refactoring_progress
        
        if validation_progress != last_progress["validation"]:
            val_msg = progress.get("validation", {}).get("message", "")
            print(f"  Validation: {validation_progress:.1f}% - {val_msg}")
            last_progress["validation"] = validation_progress
        
        if status == "completed":
            print(f"✓ Migration completed!")
            break
        elif status == "failed":
            error = status_data.get("result", {}).get("error", "Unknown error")
            return {
                "test_name": test_name,
                "success": False,
                "error": error,
                "should_fail": test_case.get("should_fail", False)
            }
        
        time.sleep(1)
    else:
        return {
            "test_name": test_name,
            "success": False,
            "error": "Migration timed out"
        }
    
    # Get final result
    final_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}")
    final_data = final_response.json()
    
    result = {
        "test_name": test_name,
        "success": True,
        "migration_id": migration_id,
        "refactored_code": final_data.get("refactored_code", ""),
        "validation": final_data.get("result", {}).get("validation", {}),
        "variable_mapping": final_data.get("variable_mapping", {})
    }
    
    # Validate results
    if test_case.get("should_fail", False):
        # If we expected failure, check if validation caught it
        validation = result.get("validation", {})
        if not validation.get("is_valid", True):
            print(f"✓ Expected failure detected by validation")
            result["validation_passed"] = True
        else:
            print(f"✗ Expected failure but validation passed")
            result["validation_passed"] = False
            result["success"] = False
    else:
        # Check for expected GCP patterns (case-insensitive, flexible matching)
        refactored_code = result.get("refactored_code", "").lower()
        expected_patterns = test_case.get("expected_gcp_patterns", [])
        should_not_contain = test_case.get("should_not_contain", [])
        
        missing_patterns = []
        for pattern in expected_patterns:
            # More flexible matching - check if any part of the pattern exists
            pattern_lower = pattern.lower()
            if pattern_lower not in refactored_code:
                # Try partial matches for common patterns
                if "google.cloud" in pattern_lower and "from google.cloud" not in refactored_code and "import google.cloud" not in refactored_code:
                    missing_patterns.append(pattern)
                elif pattern_lower not in refactored_code:
                    missing_patterns.append(pattern)
        
        found_forbidden = []
        for forbidden in should_not_contain:
            forbidden_lower = forbidden.lower()
            # Check if forbidden pattern exists (but allow in comments/strings)
            if forbidden_lower in refactored_code:
                # Basic check: if it's in a comment or string, it's less critical
                # For now, report it but don't fail if validation passed
                found_forbidden.append(forbidden)
        
        if missing_patterns:
            print(f"⚠ Missing expected patterns: {missing_patterns}")
            result["warnings"] = result.get("warnings", []) + [f"Missing patterns: {missing_patterns}"]
        
        if found_forbidden:
            print(f"✗ Found forbidden patterns: {found_forbidden}")
            result["errors"] = result.get("errors", []) + [f"Forbidden patterns found: {found_forbidden}"]
            result["success"] = False
        
        # Check validation results
        validation = result.get("validation", {})
        if not validation.get("is_valid", True):
            print(f"⚠ Validation found issues:")
            print(f"  Errors: {validation.get('errors', [])}")
            print(f"  Warnings: {validation.get('warnings', [])}")
            print(f"  AWS patterns: {validation.get('aws_patterns_found', [])}")
            print(f"  Azure patterns: {validation.get('azure_patterns_found', [])}")
            result["warnings"] = result.get("warnings", []) + validation.get("errors", [])
        
        if not missing_patterns and not found_forbidden:
            print(f"✓ All validations passed!")
    
    return result


def run_all_tests():
    """Run all test cases"""
    print("="*60)
    print("COMPREHENSIVE CODE SNIPPET TEST SUITE")
    print("="*60)
    
    # Check API health
    try:
        health_response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health_response.status_code != 200:
            print(f"✗ API health check failed: {health_response.status_code}")
            return
        print("✓ API is healthy")
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print(f"  Make sure the backend is running on {BASE_URL}")
        return
    
    results = []
    
    # Test AWS services
    print("\n" + "="*60)
    print("TESTING AWS SERVICE MIGRATIONS")
    print("="*60)
    for test_name, test_case in AWS_TEST_CASES.items():
        result = test_migration(f"aws_{test_name}", test_case)
        results.append(result)
        time.sleep(2)  # Brief pause between tests
    
    # Test Azure services
    print("\n" + "="*60)
    print("TESTING AZURE SERVICE MIGRATIONS")
    print("="*60)
    for test_name, test_case in AZURE_TEST_CASES.items():
        result = test_migration(f"azure_{test_name}", test_case)
        results.append(result)
        time.sleep(2)
    
    # Test edge cases
    print("\n" + "="*60)
    print("TESTING EDGE CASES")
    print("="*60)
    for test_name, test_case in EDGE_CASES.items():
        result = test_migration(f"edge_{test_name}", test_case)
        results.append(result)
        time.sleep(2)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("success", False))
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for result in results:
            if not result.get("success", False):
                print(f"  ✗ {result['test_name']}: {result.get('error', 'Unknown error')}")
    
    # Save detailed results
    with open("test_results_detailed.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to test_results_detailed.json")
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if all(r.get("success", False) for r in results) else 1)
