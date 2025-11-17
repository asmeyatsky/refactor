# Cloud Refactor Agent - Test Scenarios

This document outlines comprehensive test scenarios for the Universal Cloud Refactor Agent, covering all supported service migrations from AWS/Azure to GCP.

## 1. AWS S3 to Google Cloud Storage Migration

### Test Scenario 1: Basic S3 Upload/Download Operations
**Input Code:**
```python
import boto3

s3_client = boto3.client('s3')

# Upload file to S3
s3_client.upload_file('local_file.txt', 'my-bucket', 'remote_file.txt')

# Download file from S3
s3_client.download_file('my-bucket', 'remote_file.txt', 'downloaded_file.txt')

# List objects in bucket
response = s3_client.list_objects_v2(Bucket='my-bucket')
for obj in response.get('Contents', []):
    print(obj['Key'])
```

**Expected Migration:**
- Replace `boto3.client('s3')` with `google.cloud.storage.Client()`
- Replace `upload_file` with GCS upload methods
- Replace `download_file` with GCS download methods
- Replace `list_objects_v2` with GCS list methods

### Test Scenario 2: S3 Object Operations
**Input Code:**
```python
import boto3

s3 = boto3.resource('s3')
bucket = s3.Bucket('my-bucket')

# Put object
bucket.put_object(Key='key', Body=b'data')

# Get object
obj = bucket.Object('key')
content = obj.get()['Body'].read()

# Delete object
obj.delete()
```

**Expected Migration:**
- Replace `boto3.resource('s3')` with appropriate GCS resource methods
- Convert object-based operations to GCS blob operations

## 2. AWS Lambda to Google Cloud Functions Migration

### Test Scenario 1: Lambda Function Invocation
**Input Code:**
```python
import boto3

lambda_client = boto3.client('lambda')

# Invoke a Lambda function
response = lambda_client.invoke(
    FunctionName='my-function',
    InvocationType='RequestResponse',
    Payload='{"key": "value"}'
)

print(response['Payload'].read().decode())
```

**Expected Migration:**
- Replace Lambda invocation with Cloud Functions HTTP calls
- Update payload format if necessary

### Test Scenario 2: Lambda Function Definition
**Input Code:**
```python
import json

def lambda_handler(event, context):
    print('Event:', event)
    print('Context:', context)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Hello from Lambda!',
            'input': event
        })
    }
```

**Expected Migration:**
- Convert Lambda handler to Cloud Functions format
- Update function signature and response format

## 3. AWS DynamoDB to Google Cloud Firestore Migration

### Test Scenario 1: DynamoDB Item Operations
**Input Code:**
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MyTable')

# Put an item
table.put_item(
   Item={
        'id': '123',
        'name': 'John Doe',
        'email': 'john@example.com'
    }
)

# Get an item
response = table.get_item(Key={'id': '123'})
item = response['Item']

# Query items
response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('id').eq('123')
)
```

**Expected Migration:**
- Replace DynamoDB resource with Firestore client
- Convert put_item to set_document
- Convert get_item to get_document
- Convert query to Firestore query equivalents

### Test Scenario 2: DynamoDB Scan Operation
**Input Code:**
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MyTable')

# Scan all items with filter
response = table.scan(
    FilterExpression=boto3.dynamodb.conditions.Attr('age').gt(25)
)
items = response['Items']
```

**Expected Migration:**
- Replace scan with Firestore query
- Convert filter expressions to Firestore query constraints

## 4. AWS SQS to Google Cloud Pub/Sub Migration

### Test Scenario 1: SQS Message Operations
**Input Code:**
```python
import boto3

sqs = boto3.client('sqs')
queue_url = 'https://sqs.us-east-1.amazonaws.com/123456789012/my-queue'

# Send message to queue
response = sqs.send_message(
    QueueUrl=queue_url,
    DelaySeconds=10,
    MessageAttributes={
        'Title': {
            'DataType': 'String',
            'StringValue': 'The Whistler'
        }
    },
    MessageBody='Information about current NY Times fiction bestseller'
)

# Receive message from queue
response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=1,
    VisibilityTimeoutSeconds=30,
    WaitTimeSeconds=0
)
```

**Expected Migration:**
- Replace SQS client with Pub/Sub publisher/subscriber
- Convert send_message to Pub/Sub publish
- Convert receive_message to Pub/Sub pull/subscriber

### Test Scenario 2: SQS Queue Management
**Input Code:**
```python
import boto3

sqs = boto3.client('sqs')

# Create a queue
response = sqs.create_queue(
    QueueName='my-queue',
    Attributes={
        'DelaySeconds': '60',
        'MessageRetentionPeriod': '86400'
    }
)
queue_url = response['QueueUrl']
```

**Expected Migration:**
- Replace queue creation with Pub/Sub topic creation
- Convert queue attributes to Pub/Sub topic/subscription properties

## 5. AWS SNS to Google Cloud Pub/Sub Migration

### Test Scenario 1: SNS Topic Operations
**Input Code:**
```python
import boto3

sns = boto3.client('sns')

# Create a topic
response = sns.create_topic(Name='my-topic')
topic_arn = response['TopicArn']

# Publish a message
response = sns.publish(
    TopicArn=topic_arn,
    Message='Hello World!',
    Subject='Test Message'
)
```

**Expected Migration:**
- Replace SNS client with Pub/Sub publisher
- Convert topic creation and message publishing to Pub/Sub equivalents

## 6. AWS RDS to Google Cloud SQL Migration

### Test Scenario 1: RDS Database Connection
**Input Code:**
```python
import boto3
import pymysql

# Get RDS endpoint using boto3
rds = boto3.client('rds')
response = rds.describe_db_instances(DBInstanceIdentifier='mydbinstance')
endpoint = response['DBInstances'][0]['Endpoint']['Address']

# Connect using pymysql
connection = pymysql.connect(
    host=endpoint,
    user='admin',
    password='password',
    database='mydb'
)
```

**Expected Migration:**
- Replace RDS client usage with Cloud SQL connection methods
- Update connection parameters for Cloud SQL

## 7. AWS EC2 to Google Compute Engine Migration

### Test Scenario 1: EC2 Instance Management
**Input Code:**
```python
import boto3

ec2 = boto3.client('ec2')

# Launch an instance
response = ec2.run_instances(
    ImageId='ami-12345678',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.micro'
)

instance_id = response['Instances'][0]['InstanceId']

# Describe instances
response = ec2.describe_instances()
```

**Expected Migration:**
- Replace EC2 client with Compute Engine client
- Convert instance operations to GCE equivalents

## 8. AWS CloudWatch to Google Cloud Monitoring Migration

### Test Scenario 1: CloudWatch Metrics
**Input Code:**
```python
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')

# Put metric data
cloudwatch.put_metric_data(
    Namespace='MyApplication',
    MetricData=[
        {
            'MetricName': 'PageViews',
            'Value': 123.0,
            'Unit': 'Count'
        }
    ]
)

# Get metric statistics
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow(),
    Period=300,
    Statistics=['Average']
)
```

**Expected Migration:**
- Replace CloudWatch client with Cloud Monitoring client
- Convert metric operations to Monitoring API equivalents

## 9. AWS API Gateway to Google Apigee Migration

### Test Scenario 1: API Gateway Management
**Input Code:**
```python
import boto3

apigateway = boto3.client('apigateway')

# Create a REST API
response = apigateway.create_rest_api(
    name='my-rest-api',
    description='My test API'
)
api_id = response['id']

# Get APIs
response = apigateway.get_rest_apis()
```

**Expected Migration:**
- Replace API Gateway client with Apigee API client
- Convert API management to Apigee equivalents

## 10. AWS EKS to Google Kubernetes Engine Migration

### Test Scenario 1: EKS Cluster Management
**Input Code:**
```python
import boto3

eks = boto3.client('eks')

# Create a cluster
response = eks.create_cluster(
    name='my-cluster',
    roleArn='arn:aws:iam::123456789012:role/eks-service-role',
    resourcesVpcConfig={
        'subnetIds': [
            'subnet-12345',
            'subnet-67890'
        ]
    }
)

# List clusters
response = eks.list_clusters()
```

**Expected Migration:**
- Replace EKS client with GKE client
- Convert cluster management to GKE equivalents

## 11. AWS Fargate to Google Cloud Run Migration

### Test Scenario 1: Fargate Task Management
**Input Code:**
```python
import boto3

ecs = boto3.client('ecs')

# Run a task
response = ecs.run_task(
    cluster='my-cluster',
    taskDefinition='my-task-definition',
    count=1,
    startedBy='example'
)
```

**Expected Migration:**
- Replace ECS client with Cloud Run client
- Convert task execution to Cloud Run service execution

## 12. Azure Blob Storage to Google Cloud Storage Migration

### Test Scenario 1: Azure Blob Operations
**Input Code:**
```python
from azure.storage.blob import BlobServiceClient

# Create a blob service client
blob_service_client = BlobServiceClient(
    account_url="https://myaccount.blob.core.windows.net",
    credential="my_account_key"
)

# Upload a file
container_client = blob_service_client.get_container_client("mycontainer")
with open("local_file.txt", "rb") as data:
    container_client.upload_blob(name="remote_file.txt", data=data)

# Download a file
with open("download_file.txt", "wb") as my_blob:
    blob_data = container_client.download_blob("remote_file.txt")
    blob_data.readinto(my_blob)
```

**Expected Migration:**
- Replace Azure Blob client with GCS client
- Convert container operations to bucket operations

## 13. Azure Functions to Google Cloud Functions Migration

### Test Scenario 1: Azure HTTP Trigger Function
**Input Code:**
```python
import logging
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
```

**Expected Migration:**
- Convert Azure Functions signature to Cloud Functions signature
- Update HTTP request/response handling patterns

## 14. Azure Cosmos DB to Google Firestore Migration

### Test Scenario 1: Cosmos DB Item Operations
**Input Code:**
```python
import azure.cosmos.cosmos_client as cosmos_client

# Initialize the client
client = cosmos_client.CosmosClient(url_connection='https://myaccount.documents.azure.com:443/', auth={'masterKey': 'mykey'})

# Get database
database = client.GetDatabase('my-database')

# Get container
container = client.GetContainer(database['id'], 'my-container')

# Create an item
item = {
    'id': '123',
    'name': 'John Doe',
    'email': 'john@example.com'
}
container.CreateItem(body=item)
```

**Expected Migration:**
- Replace Cosmos DB client with Firestore client
- Convert database/container operations to Firestore equivalents

## 15. Azure Service Bus to Google Cloud Pub/Sub Migration

### Test Scenario 1: Service Bus Message Operations
**Input Code:**
```python
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# Create a Service Bus client
servicebus_client = ServiceBusClient.from_connection_string(conn_str="my_connection_string")

# Send a message
with servicebus_client:
    sender = servicebus_client.get_queue_sender(queue_name="myqueue")
    with sender:
        message = ServiceBusMessage("Hello World!")
        sender.send_messages(message)
```

**Expected Migration:**
- Replace Service Bus client with Pub/Sub publisher
- Convert message sending to Pub/Sub publish

## 16. Azure Event Hubs to Google Cloud Pub/Sub Migration

### Test Scenario 1: Event Hub Operations
**Input Code:**
```python
from azure.eventhub import EventHubProducerClient, EventData

# Create an Event Hub client
producer = EventHubProducerClient.from_connection_string(
    conn_str="Endpoint=sb://myeventhub.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=secretkey",
    eventhub_name="myeventhub"
)

# Send event
with producer:
    event_data_batch = producer.create_batch()
    event_data_batch.add(EventData('First event'))
    producer.send_batch(event_data_batch)
```

**Expected Migration:**
- Replace Event Hub client with Pub/Sub publisher
- Convert event publishing to Pub/Sub publish

## Migration Verification Scenarios

### Scenario 1: Authentication Translation
**Input:**
```python
import boto3
import os

# AWS credentials
os.environ['AWS_ACCESS_KEY_ID'] = 'AKIAIOSFODNN7EXAMPLE'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'

# Create S3 client
s3_client = boto3.client('s3')
```

**Expected Migration:**
- Convert AWS environment variables to GCP equivalents
- Update authentication method (AWS_ACCESS_KEY_ID → GOOGLE_APPLICATION_CREDENTIALS)

### Scenario 2: Configuration Parameter Translation
**Input:**
```python
# AWS configuration
config = {
    's3_endpoint': 'https://s3.us-west-2.amazonaws.com',
    's3_region': 'us-west-2',
    'lambda_role': 'arn:aws:iam::123456789012:role/lambda-role',
    'lambda_timeout': 30
}
```

**Expected Migration:**
- Convert AWS-specific config parameters to GCP equivalents
- s3_endpoint → gcs_endpoint
- lambda_role → gcf_service_account
- lambda_timeout → gcf_timeout

### Scenario 3: Multi-Service Migration
**Input:**
```python
import boto3

# S3 operations
s3_client = boto3.client('s3')
s3_client.upload_file('file.txt', 'bucket', 'key')

# Lambda operations
lambda_client = boto3.client('lambda')
lambda_client.invoke(FunctionName='function', Payload='{}')

# DynamoDB operations
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('table')
table.put_item(Item={'id': '123', 'data': 'value'})
```

**Expected Migration:**
- Migrate all services mentioned in the code to their GCP equivalents
- S3 → Cloud Storage
- Lambda → Cloud Functions
- DynamoDB → Firestore