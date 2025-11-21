#!/usr/bin/env python3
"""
Comprehensive Real-World Test Suite
Tests refactoring with actual AWS/Azure code patterns found in production codebases
"""

import re
import ast
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock config module before importing anything
import sys
from types import ModuleType

# Create mock config module
class MockConfig:
    GCP_PROJECT_ID = "test-project-12345"
    GCP_REGION = "us-central1"
    LOG_LEVEL = "INFO"

mock_config_module = ModuleType('config')
mock_config_module.config = MockConfig()

# Inject mock before importing
sys.modules['config'] = mock_config_module

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedASTTransformationEngine

def check_aws_azure_references(code, test_name):
    """Check for AWS/Azure references in output code"""
    aws_azure_patterns = [
        r'\bboto3\b', r'\bAWS\b(?!\w)', r'\baws\b(?!\w)', r'\bS3\b(?!\w)', r'\bs3\b(?!\w)',
        r'\bLambda\b(?!\s*[:=])', r'\bDynamoDB\b', r'\bdynamodb\b',
        r'\bSQS\b', r'\bsqs\b', r'\bSNS\b', r'\bsns\b', r'\bRDS\b', r'\brds\b',
        r'\bEC2\b', r'\bec2\b', r'\bCloudWatch\b', r'\bcloudwatch\b',
        r'\bEKS\b', r'\beks\b', r'\bFargate\b', r'\bfargate\b', r'\bECS\b', r'\becs\b',
        r'\bAzure\b(?!\w)', r'\bazure\b(?!\w)', r'\bBlobServiceClient\b',
        r'\bCosmosClient\b', r'\bServiceBusClient\b', r'\bEventHubProducerClient\b',
        r'\bazure\.storage\b', r'\bazure\.functions\b', r'\bazure\.cosmos\b',
        r'\bAWS_ACCESS_KEY_ID\b', r'\bAWS_SECRET_ACCESS_KEY\b', r'\bAWS_REGION\b',
        r'\bAWS_LAMBDA_FUNCTION_NAME\b', r'\bS3_BUCKET_NAME\b',
        r'\bAZURE_CLIENT_ID\b', r'\bAZURE_CLIENT_SECRET\b', r'\bAZURE_LOCATION\b'
    ]
    
    violations = []
    for line_num, line in enumerate(code.split('\n'), 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if '"""' in line or "'''" in line:
            continue
        for pattern in aws_azure_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                quote_count_double = line.count('"')
                quote_count_single = line.count("'")
                if quote_count_double % 2 == 0 and quote_count_single % 2 == 0:
                    violations.append(f"Line {line_num}: {pattern} in '{line.strip()}'")
                    break
    
    return violations

def check_syntax(code):
    """Check if code is syntactically valid"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def test_case(name, input_code, service_type, engine_type='aws'):
    """Run a test case"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    
    try:
        if engine_type == 'aws':
            engine = ExtendedASTTransformationEngine()
        else:
            engine = AzureExtendedASTTransformationEngine()
        
        recipe = {
            'operation': 'service_migration',
            'service_type': service_type,
            'language': 'python'
        }
        
        if engine_type == 'aws':
            output_code, _ = engine.transform_code(input_code, 'python', recipe)
        else:
            output_code = engine.transform_code(input_code, 'python', recipe)
        
        # Check syntax
        syntax_ok, syntax_error = check_syntax(output_code)
        if not syntax_ok:
            print(f"❌ SYNTAX ERROR: {syntax_error}")
            print("\nOutput code:")
            print(output_code)
            return False
        
        # Check for AWS/Azure references
        violations = check_aws_azure_references(output_code, name)
        if violations:
            print(f"❌ FAILED: Found {len(violations)} AWS/Azure references:")
            for v in violations[:5]:  # Show first 5
                print(f"  {v}")
            if len(violations) > 5:
                print(f"  ... and {len(violations) - 5} more")
            print("\nOutput code:")
            print(output_code[:500])
            return False
        
        print("✅ PASSED: No AWS/Azure references, syntax valid")
        return True
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

# Real-world AWS S3 test cases
def test_aws_s3_cases():
    """Test various AWS S3 patterns"""
    results = []
    
    # Case 1: Basic upload/download
    results.append(test_case(
        "AWS S3 - Basic upload/download",
        """
import boto3

s3_client = boto3.client('s3', region_name='us-east-1')
s3_client.upload_file('local.txt', 'my-bucket', 'remote.txt')
s3_client.download_file('my-bucket', 'remote.txt', 'downloaded.txt')
""",
        's3_to_gcs'
    ))
    
    # Case 2: Put/Get object
    results.append(test_case(
        "AWS S3 - Put/Get object",
        """
import boto3

s3 = boto3.client('s3')
s3.put_object(Bucket='my-bucket', Key='data.json', Body='{"key": "value"}')
response = s3.get_object(Bucket='my-bucket', Key='data.json')
content = response['Body'].read()
""",
        's3_to_gcs'
    ))
    
    # Case 3: List objects
    results.append(test_case(
        "AWS S3 - List objects",
        """
import boto3

s3_client = boto3.client('s3')
response = s3_client.list_objects_v2(Bucket='my-bucket')
for obj in response.get('Contents', []):
    print(obj['Key'])
""",
        's3_to_gcs'
    ))
    
    # Case 4: Delete object
    results.append(test_case(
        "AWS S3 - Delete object",
        """
import boto3

s3 = boto3.client('s3')
s3.delete_object(Bucket='my-bucket', Key='file.txt')
""",
        's3_to_gcs'
    ))
    
    # Case 5: Bucket operations
    results.append(test_case(
        "AWS S3 - Bucket operations",
        """
import boto3

s3_client = boto3.client('s3')
buckets = s3_client.list_buckets()
s3_client.create_bucket(Bucket='new-bucket', CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})
""",
        's3_to_gcs'
    ))
    
    # Case 6: S3 resource pattern
    results.append(test_case(
        "AWS S3 - Resource pattern",
        """
import boto3

s3 = boto3.resource('s3')
bucket = s3.Bucket('my-bucket')
bucket.upload_file('local.txt', 'remote.txt')
""",
        's3_to_gcs'
    ))
    
    return results

# Real-world AWS Lambda test cases
def test_aws_lambda_cases():
    """Test various AWS Lambda patterns"""
    results = []
    
    # Case 1: Basic Lambda handler
    results.append(test_case(
        "AWS Lambda - Basic handler",
        """
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Hello World'
    }
""",
        'lambda_to_cloud_functions'
    ))
    
    # Case 2: Lambda invocation
    results.append(test_case(
        "AWS Lambda - Invoke function",
        """
import boto3

lambda_client = boto3.client('lambda')
response = lambda_client.invoke(
    FunctionName='my-function',
    InvocationType='RequestResponse',
    Payload='{"key": "value"}'
)
result = response['Payload'].read()
""",
        'lambda_to_cloud_functions'
    ))
    
    # Case 3: Lambda with environment variables
    results.append(test_case(
        "AWS Lambda - With env vars",
        """
import os
import boto3

def lambda_handler(event, context):
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    s3_client = boto3.client('s3')
    return {'status': 'ok'}
""",
        'lambda_to_cloud_functions'
    ))
    
    return results

# Real-world AWS DynamoDB test cases
def test_aws_dynamodb_cases():
    """Test various AWS DynamoDB patterns"""
    results = []
    
    # Case 1: Basic DynamoDB operations
    results.append(test_case(
        "AWS DynamoDB - Basic operations",
        """
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')
table.put_item(Item={'id': '123', 'name': 'John'})
response = table.get_item(Key={'id': '123'})
""",
        'dynamodb_to_firestore'
    ))
    
    # Case 2: DynamoDB client
    results.append(test_case(
        "AWS DynamoDB - Client operations",
        """
import boto3

dynamodb_client = boto3.client('dynamodb')
dynamodb_client.put_item(
    TableName='users',
    Item={'id': {'S': '123'}, 'name': {'S': 'John'}}
)
""",
        'dynamodb_to_firestore'
    ))
    
    return results

# Real-world AWS SQS test cases
def test_aws_sqs_cases():
    """Test various AWS SQS patterns"""
    results = []
    
    # Case 1: Send/receive messages
    results.append(test_case(
        "AWS SQS - Send/receive messages",
        """
import boto3

sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/my-queue'
sqs.send_message(QueueUrl=queue_url, MessageBody='Hello World')
response = sqs.receive_message(QueueUrl=queue_url)
""",
        'sqs_to_pubsub'
    ))
    
    return results

# Real-world Azure test cases
def test_azure_cases():
    """Test various Azure patterns"""
    results = []
    
    # Case 1: Azure Blob Storage
    results.append(test_case(
        "Azure Blob Storage - Upload/download",
        """
from azure.storage.blob import BlobServiceClient

blob_service_client = BlobServiceClient(
    account_url="https://myaccount.blob.core.windows.net",
    credential="account_key"
)
container_client = blob_service_client.get_container_client("mycontainer")
with open("local_file.txt", "rb") as data:
    container_client.upload_blob(name="remote_file.txt", data=data)
""",
        'azure_blob_storage_to_gcs',
        'azure'
    ))
    
    # Case 2: Azure Functions
    results.append(test_case(
        "Azure Functions - HTTP trigger",
        """
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    name = req.params.get('name')
    return func.HttpResponse(f"Hello {name}")
""",
        'azure_functions_to_cloud_functions',
        'azure'
    ))
    
    # Case 3: Azure Cosmos DB
    results.append(test_case(
        "Azure Cosmos DB - Basic operations",
        """
import azure.cosmos.cosmos_client as cosmos_client

client = cosmos_client.CosmosClient(
    url_connection='https://myaccount.documents.azure.com:443/',
    auth={'masterKey': 'mykey'}
)
database = client.GetDatabase('my-database')
container = database.GetContainer('my-container')
container.create_item(body={'id': '123', 'name': 'John'})
""",
        'azure_cosmos_db_to_firestore',
        'azure'
    ))
    
    # Case 4: Azure Service Bus
    results.append(test_case(
        "Azure Service Bus - Send message",
        """
from azure.servicebus import ServiceBusClient, ServiceBusMessage

servicebus_client = ServiceBusClient.from_connection_string(
    conn_str="connection_string"
)
with servicebus_client:
    sender = servicebus_client.get_queue_sender(queue_name="myqueue")
    message = ServiceBusMessage("Hello World")
    sender.send_messages(message)
""",
        'azure_service_bus_to_pubsub',
        'azure'
    ))
    
    return results

# Additional real-world patterns from production codebases
def test_additional_patterns():
    """Test additional patterns found in production codebases"""
    results = []
    
    # Case 1: S3 with presigned URLs
    results.append(test_case(
        "S3 - Presigned URL generation",
        """
import boto3
from botocore.config import Config

s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
url = s3_client.generate_presigned_url('get_object', Params={'Bucket': 'my-bucket', 'Key': 'file.txt'}, ExpiresIn=3600)
""",
        's3_to_gcs'
    ))
    
    # Case 2: S3 with multipart upload
    results.append(test_case(
        "S3 - Multipart upload",
        """
import boto3

s3 = boto3.client('s3')
response = s3.create_multipart_upload(Bucket='my-bucket', Key='large-file.zip')
upload_id = response['UploadId']
""",
        's3_to_gcs'
    ))
    
    # Case 3: Lambda with S3 event trigger
    results.append(test_case(
        "Lambda - S3 event trigger handler",
        """
import boto3
import json

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(obj['Body'].read())
    return {'statusCode': 200}
""",
        'lambda_to_cloud_functions'
    ))
    
    # Case 4: DynamoDB batch operations
    results.append(test_case(
        "DynamoDB - Batch write",
        """
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')
with table.batch_writer() as batch:
    batch.put_item(Item={'id': '1', 'name': 'John'})
    batch.put_item(Item={'id': '2', 'name': 'Jane'})
""",
        'dynamodb_to_firestore'
    ))
    
    # Case 5: SQS with FIFO queue
    results.append(test_case(
        "SQS - FIFO queue operations",
        """
import boto3

sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/my-queue.fifo'
sqs.send_message(
    QueueUrl=queue_url,
    MessageBody='Hello',
    MessageGroupId='group1',
    MessageDeduplicationId='dedup1'
)
""",
        'sqs_to_pubsub'
    ))
    
    # Case 6: Azure Blob with SAS token
    results.append(test_case(
        "Azure Blob - SAS token generation",
        """
from azure.storage.blob import BlobServiceClient, generate_account_sas, ResourceTypes, AccountSasPermissions
from datetime import datetime, timedelta

blob_service_client = BlobServiceClient(account_url="https://myaccount.blob.core.windows.net", credential="key")
sas_token = generate_account_sas(
    account_name="myaccount",
    account_key="key",
    resource_types=ResourceTypes(object=True),
    permission=AccountSasPermissions(read=True),
    expiry=datetime.utcnow() + timedelta(hours=1)
)
""",
        'azure_blob_storage_to_gcs',
        'azure'
    ))
    
    # Case 7: Azure Functions with Cosmos DB
    results.append(test_case(
        "Azure Functions - Cosmos DB trigger",
        """
import azure.functions as func
import azure.cosmos.cosmos_client as cosmos_client

def main(documents: func.DocumentList) -> str:
    client = cosmos_client.CosmosClient(
        url_connection='https://myaccount.documents.azure.com:443/',
        auth={'masterKey': 'key'}
    )
    database = client.GetDatabase('mydb')
    return 'Processed'
""",
        'azure_functions_to_cloud_functions',
        'azure'
    ))
    
    # Case 8: S3 with versioning
    results.append(test_case(
        "S3 - Versioned objects",
        """
import boto3

s3 = boto3.client('s3')
versions = s3.list_object_versions(Bucket='my-bucket', Prefix='file.txt')
for version in versions.get('Versions', []):
    print(version['VersionId'])
""",
        's3_to_gcs'
    ))
    
    return results

# Edge cases and complex scenarios
def test_edge_cases():
    """Test edge cases and complex scenarios"""
    results = []
    
    # Case 1: Multiple services in one file
    results.append(test_case(
        "Edge Case - Multiple AWS services",
        """
import boto3

s3 = boto3.client('s3')
s3.upload_file('file.txt', 'bucket', 'key.txt')

lambda_client = boto3.client('lambda')
lambda_client.invoke(FunctionName='func', Payload='{}')
""",
        's3_to_gcs'  # Will auto-detect
    ))
    
    # Case 2: With error handling
    results.append(test_case(
        "Edge Case - With error handling",
        """
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

try:
    s3 = boto3.client('s3')
    s3.upload_file('file.txt', 'bucket', 'key.txt')
except NoCredentialsError:
    print("No credentials")
except ClientError as e:
    print(f"Error: {e}")
""",
        's3_to_gcs'
    ))
    
    # Case 3: With region specification
    results.append(test_case(
        "Edge Case - Region specification",
        """
import boto3

s3_client = boto3.client('s3', region_name='us-west-2')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
""",
        's3_to_gcs'
    ))
    
    # Case 4: Lambda with S3 access
    results.append(test_case(
        "Edge Case - Lambda accessing S3",
        """
import boto3
import json

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket = event['bucket']
    key = event['key']
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = json.loads(obj['Body'].read())
    return data
""",
        'lambda_to_cloud_functions'
    ))
    
    return results

def main():
    print("="*70)
    print("COMPREHENSIVE REAL-WORLD REFACTORING TEST SUITE")
    print("="*70)
    
    all_results = []
    
    print("\n" + "="*70)
    print("AWS S3 TEST CASES")
    print("="*70)
    all_results.extend(test_aws_s3_cases())
    
    print("\n" + "="*70)
    print("AWS LAMBDA TEST CASES")
    print("="*70)
    all_results.extend(test_aws_lambda_cases())
    
    print("\n" + "="*70)
    print("AWS DYNAMODB TEST CASES")
    print("="*70)
    all_results.extend(test_aws_dynamodb_cases())
    
    print("\n" + "="*70)
    print("AWS SQS TEST CASES")
    print("="*70)
    all_results.extend(test_aws_sqs_cases())
    
    print("\n" + "="*70)
    print("AZURE TEST CASES")
    print("="*70)
    all_results.extend(test_azure_cases())
    
    print("\n" + "="*70)
    print("ADDITIONAL REAL-WORLD PATTERNS")
    print("="*70)
    all_results.extend(test_additional_patterns())
    
    print("\n" + "="*70)
    print("EDGE CASES")
    print("="*70)
    all_results.extend(test_edge_cases())
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(all_results)
    total = len(all_results)
    print(f"Passed: {passed}/{total} ({passed*100//total}%)")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - REFACTORING IS PERFECT!")
    else:
        print(f"❌ {total - passed} TESTS FAILED")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    exit(main())
