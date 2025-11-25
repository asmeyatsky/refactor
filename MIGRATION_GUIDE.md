# Migration Guide

## DynamoDB to Firestore Migration

The tool intelligently handles two types of DynamoDB code:

### 1. Migration Scripts

Migration scripts that read from DynamoDB and write to Firestore are automatically detected. The tool preserves boto3 for reading operations while converting write operations to Firestore.

**Example Migration Script:**
```python
import boto3
import firebase_admin
from firebase_admin import credentials, firestore
from decimal import Decimal

# Initialize DynamoDB (source) - PRESERVED
dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
source_table = dynamodb_resource.Table('SourceDynamoTable')

# Initialize Firestore (destination) - ADDED
if not firebase_admin._apps:
    cred = credentials.Certificate('path/to/service-account.json')
    firebase_admin.initialize_app(cred)

firestore_db = firestore.Client()

# Scan DynamoDB - PRESERVED
response = source_table.scan()
items = response.get('Items', [])

# Write to Firestore - CONVERTED
for item in items:
    clean_item = convert_decimal(item)
    doc_ref = firestore_db.collection('DestinationCollection').document()
    doc_ref.set(clean_item)
```

**Detection Criteria:**
- Contains both read operations (`.scan()`, `.get_item()`, `.query()`) AND write operations (`.put_item()`, `.batch_write_item()`)
- Automatically preserves boto3 imports and DynamoDB client initialization
- Converts write operations to Firestore equivalents

### 2. Application Code

Application code that uses DynamoDB is fully converted to Firestore.

**Example Application Code:**
```python
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
```

**Converted to:**
```python
from google.cloud import firestore

firestore_db = firestore.Client()
collection_ref = firestore_db.collection(os.getenv('FIRESTORE_COLLECTION_NAME', 'my-collection'))

# Put item
doc_ref = collection_ref.document('123')
doc_ref.set({
    'name': 'Test Item',
    'value': 42
})
```

## Testing

Comprehensive test suites are available:

### Python Tests
- `test_aws_comprehensive.py`: Full API-based test suite for all AWS services
- `test_migration_direct.py`: Direct function testing without API server

### Test Coverage
- S3 (basic operations, presigned URLs)
- Lambda (handlers, S3 integration)
- DynamoDB (basic operations, migration scripts)
- SQS (send/receive messages)
- SNS (publish messages)
- Multi-service migrations
- Java code migrations

## Key Features

1. **Automatic Detection**: The tool automatically detects migration scripts vs application code
2. **Preservation**: Migration scripts preserve AWS SDK for reading operations
3. **Complete Conversion**: Application code is fully converted to GCP equivalents
4. **Type Conversion**: Automatically handles Decimal type conversion for DynamoDB → Firestore
5. **Batch Operations**: Converts DynamoDB batch operations to Firestore batch operations

## Best Practices

1. **Migration Scripts**: Use clear variable names like `source_table` and `firestore_db` to help the tool detect migration patterns
2. **Application Code**: Use standard DynamoDB patterns for best conversion results
3. **Testing**: Always test migrated code thoroughly, especially for migration scripts
4. **Credentials**: Ensure AWS credentials are configured for migration scripts that read from DynamoDB
