"""
Extended Cloud Refactor Agent - Example Usage

This script demonstrates the usage of the extended Cloud Refactor Agent
for multi-service AWS to GCP migrations.
"""

import tempfile
import os
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
import sys
sys.path.insert(0, str(project_root))

from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
from domain.entities.codebase import ProgrammingLanguage


def create_sample_codebase():
    """Create a sample codebase with multiple AWS services for testing"""
    # Create a temporary directory for our sample codebase
    temp_dir = tempfile.mkdtemp(prefix="aws_codebase_")
    
    # Create a Python file with AWS S3 usage
    s3_file_content = '''
import boto3
from botocore.exceptions import ClientError

def upload_file_to_s3(file_path, bucket, key):
    """Upload a file to an S3 bucket"""
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_path, bucket, key)
        print(f"File {file_path} uploaded to {bucket}/{key}")
    except ClientError as e:
        print(f"Error uploading file: {e}")
        return False
    return True

def download_file_from_s3(bucket, key, file_path):
    """Download a file from an S3 bucket"""
    s3_client = boto3.client('s3')
    try:
        s3_client.download_file(bucket, key, file_path)
        print(f"File {bucket}/{key} downloaded to {file_path}")
    except ClientError as e:
        print(f"Error downloading file: {e}")
        return False
    return True
'''

    # Create a Python file with AWS Lambda usage
    lambda_file_content = '''
import boto3
import json
from botocore.exceptions import ClientError

def invoke_lambda_function(function_name, payload):
    """Invoke an AWS Lambda function"""
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode())
        return result
    except ClientError as e:
        print(f"Error invoking Lambda: {e}")
        return None

def list_lambda_functions():
    """List all Lambda functions"""
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.list_functions()
        functions = response['Functions']
        return [f['FunctionName'] for f in functions]
    except ClientError as e:
        print(f"Error listing Lambda functions: {e}")
        return []
'''

    # Create a Python file with AWS DynamoDB usage
    dynamodb_file_content = '''
import boto3
from botocore.exceptions import ClientError

def create_dynamodb_table(table_name):
    """Create a DynamoDB table"""
    dynamodb = boto3.client('dynamodb')
    
    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        return response
    except ClientError as e:
        print(f"Error creating table: {e}")
        return None

def put_item_in_dynamodb(table_name, item):
    """Put an item in DynamoDB table"""
    dynamodb = boto3.client('dynamodb')
    
    try:
        response = dynamodb.put_item(
            TableName=table_name,
            Item=item
        )
        return response
    except ClientError as e:
        print(f"Error putting item: {e}")
        return None

def get_item_from_dynamodb(table_name, key):
    """Get an item from DynamoDB table"""
    dynamodb = boto3.client('dynamodb')
    
    try:
        response = dynamodb.get_item(
            TableName=table_name,
            Key=key
        )
        return response.get('Item')
    except ClientError as e:
        print(f"Error getting item: {e}")
        return None
'''

    # Write the sample files
    with open(os.path.join(temp_dir, "s3_operations.py"), "w") as f:
        f.write(s3_file_content)
    
    with open(os.path.join(temp_dir, "lambda_operations.py"), "w") as f:
        f.write(lambda_file_content)
    
    with open(os.path.join(temp_dir, "dynamodb_operations.py"), "w") as f:
        f.write(dynamodb_file_content)
    
    return temp_dir


def main():
    print("Creating sample codebase with multiple AWS services...")
    sample_codebase_path = create_sample_codebase()
    
    print(f"Sample codebase created at: {sample_codebase_path}")
    
    # List files in the sample codebase
    print("\nFiles in sample codebase:")
    for file in os.listdir(sample_codebase_path):
        print(f"  - {file}")
    
    print("\nStarting multi-service AWS to GCP migration...")
    
    # Create the multi-service migration system
    orchestrator = create_multi_service_migration_system()
    
    # Execute a migration with auto-detection
    result = orchestrator.execute_migration(
        codebase_path=sample_codebase_path,
        language=ProgrammingLanguage.PYTHON
    )
    
    print(f"\nMigration completed: {result['migration_id']}")
    print(f"Success: {result['verification_result']['success']}")
    print(f"Migration Type: {result['migration_type']}")
    
    if result['execution_result'].get('service_results'):
        print(f"\nService Migration Results:")
        for service, stats in result['execution_result']['service_results'].items():
            print(f"  {service}: {stats.get('success', 0)} successful, {stats.get('failed', 0)} failed")
    
    # Also try migrating specific services
    print("\n" + "="*60)
    print("Testing migration with specific services...")
    
    result2 = orchestrator.execute_migration(
        codebase_path=sample_codebase_path,
        language=ProgrammingLanguage.PYTHON,
        services_to_migrate=["s3", "lambda"]
    )
    
    print(f"\nSpecific services migration completed: {result2['migration_id']}")
    print(f"Success: {result2['verification_result']['success']}")
    
    if result2['execution_result'].get('service_results'):
        print(f"\nService Migration Results:")
        for service, stats in result2['execution_result']['service_results'].items():
            print(f"  {service}: {stats.get('success', 0)} successful, {stats.get('failed', 0)} failed")
    
    # Clean up - remove the temporary codebase
    import shutil
    shutil.rmtree(sample_codebase_path)
    print(f"\nCleaned up temporary codebase: {sample_codebase_path}")


if __name__ == "__main__":
    main()