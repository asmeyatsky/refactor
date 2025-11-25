"""
Comprehensive AWS to GCP migration test suite
Tests all AWS services with real-world code examples
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

# Comprehensive AWS Python test cases
AWS_PYTHON_TESTS = {
    "s3_basic": {
        "code": """import boto3
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
        "expected": ["google.cloud.storage", "storage.Client", "GCS_BUCKET_NAME"],
        "forbidden": ["boto3", "s3_client", "S3_BUCKET_NAME"]
    },
    
    "s3_presigned_url": {
        "code": """import boto3
from datetime import timedelta

s3_client = boto3.client('s3')
bucket = 'my-bucket'
key = 'my-file.txt'

# Generate presigned URL
url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=3600
)
print(f"Presigned URL: {url}")
""",
        "services": ["s3"],
        "expected": ["google.cloud.storage", "generate_signed_url"],
        "forbidden": ["boto3", "s3_client"]
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
        "expected": ["google.cloud.functions", "def process"],
        "forbidden": ["lambda_handler", "event['Records']"]
    },
    
    "lambda_with_s3": {
        "code": """import json
import boto3
import os

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    bucket = os.getenv('S3_BUCKET_NAME')
    
    # Read from S3
    response = s3_client.get_object(Bucket=bucket, Key='input.json')
    data = json.loads(response['Body'].read())
    
    # Process data
    processed = {'processed': True, 'data': data}
    
    # Write to S3
    s3_client.put_object(
        Bucket=bucket,
        Key='output.json',
        Body=json.dumps(processed)
    )
    
    return {'statusCode': 200, 'body': json.dumps(processed)}
""",
        "services": ["lambda", "s3"],
        "expected": ["google.cloud.functions", "google.cloud.storage"],
        "forbidden": ["lambda_handler", "boto3", "s3_client"]
    },
    
    "dynamodb_basic": {
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
        "expected": ["google.cloud.firestore", "firestore.Client"],
        "forbidden": ["boto3", "dynamodb", "DYNAMODB_TABLE_NAME"]
    },
    
    "dynamodb_migration_script": {
        "code": """import boto3
import firebase_admin
from firebase_admin import credentials, firestore
from decimal import Decimal

# Initialize DynamoDB (source)
dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
source_table = dynamodb_resource.Table('SourceDynamoTable')

# Initialize Firestore (destination)
if not firebase_admin._apps:
    cred = credentials.Certificate('path/to/service-account.json')
    firebase_admin.initialize_app(cred)

firestore_db = firestore.Client()

# Scan DynamoDB table
response = source_table.scan()
items = response.get('Items', [])

# Write to Firestore
for item in items:
    clean_item = convert_decimal(item)
    doc_ref = firestore_db.collection('DestinationCollection').document()
    doc_ref.set(clean_item)

def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    return obj
""",
        "services": ["dynamodb"],
        "expected": ["boto3", "firestore.Client", "scan", "set"],
        "forbidden": []  # Should preserve boto3 for reading
    },
    
    "sqs_basic": {
        "code": """import boto3
import os
import json

sqs = boto3.client('sqs', region_name='us-east-1')
queue_url = os.getenv('SQS_QUEUE_URL')

# Send message
response = sqs.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps({'key': 'value'})
)

# Receive messages
messages = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=10
)
for msg in messages.get('Messages', []):
    print(msg['Body'])
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg['ReceiptHandle'])
""",
        "services": ["sqs"],
        "expected": ["google.cloud.pubsub", "PublisherClient"],
        "forbidden": ["boto3", "sqs", "SQS_QUEUE_URL"]
    },
    
    "sns_basic": {
        "code": """import boto3
import os
import json

sns = boto3.client('sns', region_name='us-east-1')
topic_arn = os.getenv('SNS_TOPIC_ARN')

# Publish message
response = sns.publish(
    TopicArn=topic_arn,
    Message=json.dumps({'key': 'value'}),
    Subject='Test Subject'
)
""",
        "services": ["sns"],
        "expected": ["google.cloud.pubsub", "PublisherClient"],
        "forbidden": ["boto3", "sns", "SNS_TOPIC_ARN"]
    },
    
    "rds_connection": {
        "code": """import pymysql
import os

# Connect to RDS MySQL
connection = pymysql.connect(
    host=os.getenv('RDS_HOST'),
    user=os.getenv('RDS_USER'),
    password=os.getenv('RDS_PASSWORD'),
    database=os.getenv('RDS_DATABASE'),
    port=int(os.getenv('RDS_PORT', 3306))
)

cursor = connection.cursor()
cursor.execute("SELECT * FROM users")
results = cursor.fetchall()
""",
        "services": ["rds"],
        "expected": ["google.cloud.sql", "CloudSqlConnection"],
        "forbidden": ["pymysql", "RDS_HOST"]
    },
    
    "multi_service_lambda": {
        "code": """import json
import boto3
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    # Read from S3
    bucket = os.getenv('S3_BUCKET_NAME')
    response = s3_client.get_object(Bucket=bucket, Key='data.json')
    data = json.loads(response['Body'].read())
    
    # Write to DynamoDB
    table = dynamodb.Table(os.getenv('DYNAMODB_TABLE_NAME'))
    table.put_item(Item=data)
    
    # Send to SQS
    queue_url = os.getenv('SQS_QUEUE_URL')
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(data)
    )
    
    return {'statusCode': 200}
""",
        "services": ["lambda", "s3", "dynamodb", "sqs"],
        "expected": ["google.cloud.functions", "google.cloud.storage", "google.cloud.firestore", "google.cloud.pubsub"],
        "forbidden": ["boto3", "lambda_handler", "s3_client", "dynamodb", "sqs"]
    }
}

# AWS Java test cases
AWS_JAVA_TESTS = {
    "s3_java": {
        "code": """import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import com.amazonaws.services.s3.model.PutObjectRequest;
import java.io.File;

public class S3Example {
    private AmazonS3 s3Client;
    
    public S3Example() {
        s3Client = AmazonS3ClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void uploadFile(String bucketName, String key, File file) {
        PutObjectRequest request = new PutObjectRequest(bucketName, key, file);
        s3Client.putObject(request);
    }
}
""",
        "services": ["s3"],
        "language": "java",
        "expected": ["com.google.cloud.storage", "Storage"],
        "forbidden": ["com.amazonaws", "AmazonS3"]
    },
    
    "lambda_java": {
        "code": """import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import java.util.Map;

public class LambdaHandler implements RequestHandler<Map<String, Object>, Map<String, Object>> {
    @Override
    public Map<String, Object> handleRequest(Map<String, Object> input, Context context) {
        return Map.of("statusCode", 200, "body", "Hello from Lambda!");
    }
}
""",
        "services": ["lambda"],
        "language": "java",
        "expected": ["com.google.cloud.functions", "HttpFunction"],
        "forbidden": ["com.amazonaws", "RequestHandler"]
    },
    
    "dynamodb_java": {
        "code": """import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder;
import com.amazonaws.services.dynamodbv2.model.PutItemRequest;
import java.util.HashMap;
import java.util.Map;

public class DynamoDBExample {
    private AmazonDynamoDB dynamoDB;
    
    public DynamoDBExample() {
        dynamoDB = AmazonDynamoDBClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void putItem(String tableName, Map<String, Object> item) {
        PutItemRequest request = new PutItemRequest()
            .withTableName(tableName)
            .withItem(convertToAttributeValues(item));
        dynamoDB.putItem(request);
    }
    
    private Map<String, com.amazonaws.services.dynamodbv2.model.AttributeValue> convertToAttributeValues(Map<String, Object> item) {
        // Conversion logic
        return new HashMap<>();
    }
}
""",
        "services": ["dynamodb"],
        "language": "java",
        "expected": ["com.google.cloud.firestore", "Firestore"],
        "forbidden": ["com.amazonaws", "AmazonDynamoDB"]
    }
}


def test_migration(test_name: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single migration case"""
    print(f"\n{'='*70}")
    print(f"Testing: {test_name}")
    print(f"{'='*70}")
    
    language = test_case.get("language", "python")
    services = test_case.get("services", [])
    code = test_case.get("code", "")
    
    print(f"Language: {language}")
    print(f"Services: {services}")
    
    # Submit migration request
    try:
        response = requests.post(
            f"{BASE_URL}/api/migrate",
            json={
                "code": code,
                "language": language,
                "services": services,
                "cloud_provider": "aws"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
        
        migration_id = response.json()["migration_id"]
        print(f"Migration ID: {migration_id}")
        
    except Exception as e:
        return {
            "test_name": test_name,
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
    
    # Poll for completion
    max_wait = 180
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            status_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}", timeout=10)
            if status_response.status_code != 200:
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": f"Status check failed: {status_response.status_code}"
                }
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            progress = status_data.get("progress", {})
            ref_progress = progress.get("refactoring", {}).get("progress", 0.0)
            val_progress = progress.get("validation", {}).get("progress", 0.0)
            
            if ref_progress > 0 or val_progress > 0:
                print(f"  Progress: Refactoring {ref_progress:.1f}%, Validation {val_progress:.1f}%")
            
            if status == "completed":
                print(f"✓ Migration completed!")
                break
            elif status == "failed":
                error = status_data.get("result", {}).get("error", "Unknown error")
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": error
                }
            
            time.sleep(2)
        except Exception as e:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"Polling error: {str(e)}"
            }
    else:
        return {
            "test_name": test_name,
            "success": False,
            "error": "Migration timed out"
        }
    
    # Get final result
    try:
        final_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}", timeout=10)
        final_data = final_response.json()
        
        refactored_code = final_data.get("result", {}).get("refactored_code", "")
        validation = final_data.get("result", {}).get("validation", {})
        
        result = {
            "test_name": test_name,
            "success": True,
            "migration_id": migration_id,
            "refactored_code": refactored_code,
            "validation": validation
        }
        
        # Validate results
        refactored_lower = refactored_code.lower()
        expected = test_case.get("expected", [])
        forbidden = test_case.get("forbidden", [])
        
        missing = []
        for pattern in expected:
            pattern_lower = pattern.lower()
            if pattern_lower not in refactored_lower:
                missing.append(pattern)
        
        found_forbidden = []
        for pattern in forbidden:
            pattern_lower = pattern.lower()
            if pattern_lower in refactored_lower:
                found_forbidden.append(pattern)
        
        if missing:
            print(f"⚠ Missing expected patterns: {missing}")
            result["warnings"] = result.get("warnings", []) + [f"Missing: {missing}"]
        
        if found_forbidden:
            print(f"✗ Found forbidden patterns: {found_forbidden}")
            result["errors"] = result.get("errors", []) + [f"Forbidden: {found_forbidden}"]
            # Don't fail if it's a migration script (should preserve boto3)
            if "migration" not in test_name.lower():
                result["success"] = False
        
        # Check validation
        if not validation.get("is_valid", True):
            val_errors = validation.get("errors", [])
            val_warnings = validation.get("warnings", [])
            print(f"⚠ Validation issues:")
            if val_errors:
                print(f"  Errors: {val_errors}")
            if val_warnings:
                print(f"  Warnings: {val_warnings}")
            result["validation_errors"] = val_errors
            result["validation_warnings"] = val_warnings
        
        if not missing and not found_forbidden:
            print(f"✓ All validations passed!")
        
        return result
        
    except Exception as e:
        return {
            "test_name": test_name,
            "success": False,
            "error": f"Failed to get result: {str(e)}"
        }


def run_all_tests():
    """Run all test cases"""
    print("="*70)
    print("COMPREHENSIVE AWS TO GCP MIGRATION TEST SUITE")
    print("="*70)
    
    # Check API health
    try:
        health_response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health_response.status_code != 200:
            print(f"✗ API health check failed: {health_response.status_code}")
            return []
        print("✓ API is healthy")
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print(f"  Make sure the backend is running on {BASE_URL}")
        return []
    
    results = []
    
    # Test AWS Python services
    print("\n" + "="*70)
    print("TESTING AWS PYTHON SERVICE MIGRATIONS")
    print("="*70)
    for test_name, test_case in AWS_PYTHON_TESTS.items():
        result = test_migration(f"aws_python_{test_name}", test_case)
        results.append(result)
        time.sleep(1)
    
    # Test AWS Java services
    print("\n" + "="*70)
    print("TESTING AWS JAVA SERVICE MIGRATIONS")
    print("="*70)
    for test_name, test_case in AWS_JAVA_TESTS.items():
        result = test_migration(f"aws_java_{test_name}", test_case)
        results.append(result)
        time.sleep(1)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
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
    with open("test_aws_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to test_aws_results.json")
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if all(r.get("success", False) for r in results) else 1)
