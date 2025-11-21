# GCP Variables Reference Guide

This document provides a comprehensive list of GCP-specific environment variables and configuration parameters that should be used in refactored code. These variables replace AWS and Azure equivalents.

## Core GCP Configuration Variables

### Project & Region
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_PROJECT_ID` | The ID of the GCP project the application runs in | `AWS_ACCOUNT_ID`, `AZURE_SUBSCRIPTION_ID` | `my-project-12345` |
| `GCP_REGION` | The GCP region where resources are deployed | `AWS_REGION`, `AZURE_LOCATION` | `us-central1`, `asia-south1` |
| `GCP_ZONE` | The GCP zone (optional, more specific than region) | `AWS_AVAILABILITY_ZONE` | `us-central1-a` |
| `GOOGLE_CLOUD_PROJECT` | Alternative environment variable for project ID (used by gcloud CLI) | `AWS_ACCOUNT_ID` | `my-project-12345` |

## Storage Variables

### Cloud Storage (GCS)
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCS_BUCKET_NAME` | The name of the Google Cloud Storage bucket | `S3_BUCKET_NAME`, `AZURE_STORAGE_CONTAINER` | `my-app-storage` |
| `GCS_BUCKET_LOCATION` | The location/region of the GCS bucket | `S3_BUCKET_REGION` | `us-central1` |
| `GCS_BLOB_NAME` | The name/path of a blob (object) in GCS | `S3_KEY`, `S3_OBJECT_KEY`, `AZURE_BLOB_NAME` | `data/file.txt` |
| `GCS_STORAGE_CLASS` | Storage class for GCS bucket (STANDARD, NEARLINE, COLDLINE, ARCHIVE) | `S3_STORAGE_CLASS` | `STANDARD` |
| `GCS_ENCRYPTION_KEY` | Customer-managed encryption key for GCS | `S3_KMS_KEY_ID` | `projects/my-project/locations/us/keyRings/my-ring/cryptoKeys/my-key` |

## Compute Variables

### Cloud Functions
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_FUNCTION_NAME` | The name of the Cloud Function | `AWS_LAMBDA_FUNCTION_NAME`, `AZURE_FUNCTION_NAME` | `my-function` |
| `GCP_FUNCTION_REGION` | The region where the function is deployed | `AWS_LAMBDA_REGION` | `us-central1` |
| `GCP_FUNCTION_URL` | The HTTP trigger URL for the function | `AWS_LAMBDA_FUNCTION_URL` | `https://us-central1-my-project.cloudfunctions.net/my-function` |
| `GCP_FUNCTION_RUNTIME` | The runtime environment (python39, nodejs18, etc.) | `AWS_LAMBDA_RUNTIME` | `python39` |
| `GCP_FUNCTION_ENTRY_POINT` | The entry point function name | `AWS_LAMBDA_HANDLER` | `function_handler` |
| `GCP_FUNCTION_MEMORY` | Memory allocation in MB | `AWS_LAMBDA_MEMORY_SIZE` | `256` |
| `GCP_FUNCTION_TIMEOUT` | Function timeout in seconds | `AWS_LAMBDA_TIMEOUT` | `60` |

### Cloud Run
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_CLOUD_RUN_SERVICE_NAME` | The name of the Cloud Run service | `AWS_FARGATE_SERVICE_NAME`, `AZURE_CONTAINER_INSTANCE_NAME` | `my-service` |
| `GCP_CLOUD_RUN_REGION` | The region where Cloud Run service is deployed | `AWS_FARGATE_REGION` | `us-central1` |
| `GCP_CLOUD_RUN_URL` | The service URL | `AWS_ECS_SERVICE_URL` | `https://my-service-xyz.run.app` |
| `GCP_CLOUD_RUN_IMAGE` | Container image URL | `AWS_ECS_TASK_DEFINITION_IMAGE` | `gcr.io/my-project/my-image:latest` |

### Compute Engine
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_INSTANCE_NAME` | The name of the Compute Engine instance | `AWS_EC2_INSTANCE_ID`, `AZURE_VM_NAME` | `my-instance` |
| `GCP_INSTANCE_ZONE` | The zone where the instance is located | `AWS_EC2_AVAILABILITY_ZONE` | `us-central1-a` |
| `GCP_INSTANCE_MACHINE_TYPE` | The machine type | `AWS_EC2_INSTANCE_TYPE`, `AZURE_VM_SIZE` | `n1-standard-1` |
| `GCP_INSTANCE_PROJECT` | The project ID for the instance | `AWS_ACCOUNT_ID` | `my-project-12345` |

## Database Variables

### Cloud SQL
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_CLOUD_SQL_INSTANCE_CONNECTION_NAME` | Full connection name for Cloud SQL | `RDS_ENDPOINT`, `AZURE_SQL_SERVER` | `my-project:us-central1:my-instance` |
| `GCP_CLOUD_SQL_INSTANCE_NAME` | Instance name | `RDS_DB_INSTANCE_IDENTIFIER` | `my-instance` |
| `GCP_CLOUD_SQL_DATABASE_NAME` | Database name | `RDS_DB_NAME`, `AZURE_SQL_DATABASE` | `my_database` |
| `GCP_CLOUD_SQL_USER` | Database user | `RDS_USERNAME`, `AZURE_SQL_USER` | `db_user` |
| `GCP_CLOUD_SQL_PASSWORD` | Database password | `RDS_PASSWORD`, `AZURE_SQL_PASSWORD` | `secure_password` |
| `GCP_CLOUD_SQL_HOST` | Database host (when using public IP) | `RDS_HOSTNAME` | `1.2.3.4` |
| `GCP_CLOUD_SQL_PORT` | Database port | `RDS_PORT`, `AZURE_SQL_PORT` | `5432` |

### Firestore
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_FIRESTORE_PROJECT_ID` | Firestore project ID | `DYNAMODB_REGION`, `AZURE_COSMOS_DB_ACCOUNT` | `my-project-12345` |
| `GCP_FIRESTORE_DATABASE_ID` | Firestore database ID (default: "(default)") | `DYNAMODB_TABLE_NAME`, `AZURE_COSMOS_DB_NAME` | `(default)` |
| `GCP_FIRESTORE_COLLECTION_NAME` | Collection name | `DYNAMODB_TABLE_NAME`, `AZURE_COSMOS_CONTAINER` | `users` |

### Bigtable
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_BIGTABLE_INSTANCE_ID` | Bigtable instance ID | `DYNAMODB_TABLE_NAME` | `my-instance` |
| `GCP_BIGTABLE_TABLE_ID` | Table ID | `DYNAMODB_TABLE_NAME` | `my-table` |

## Messaging Variables

### Pub/Sub
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_PUBSUB_TOPIC_ID` | Pub/Sub topic ID | `SNS_TOPIC_ARN`, `SQS_QUEUE_URL`, `AZURE_SERVICE_BUS_TOPIC` | `my-topic` |
| `GCP_PUBSUB_SUBSCRIPTION_ID` | Subscription ID | `SQS_QUEUE_NAME`, `AZURE_SERVICE_BUS_SUBSCRIPTION` | `my-subscription` |
| `GCP_PUBSUB_PROJECT_ID` | Project ID for Pub/Sub | `AWS_ACCOUNT_ID` | `my-project-12345` |
| `GCP_PUBSUB_TOPIC_FULL_NAME` | Full topic path | `SNS_TOPIC_ARN` | `projects/my-project/topics/my-topic` |
| `GCP_PUBSUB_SUBSCRIPTION_FULL_NAME` | Full subscription path | `SQS_QUEUE_URL` | `projects/my-project/subscriptions/my-subscription` |

## Monitoring & Logging Variables

### Cloud Monitoring
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_MONITORING_PROJECT_ID` | Project ID for monitoring | `AWS_CLOUDWATCH_NAMESPACE`, `AZURE_MONITOR_WORKSPACE` | `my-project-12345` |
| `GCP_MONITORING_METRIC_TYPE` | Custom metric type | `AWS_CLOUDWATCH_METRIC_NAME` | `custom.googleapis.com/my-metric` |
| `GCP_MONITORING_RESOURCE_TYPE` | Monitored resource type | `AWS_CLOUDWATCH_DIMENSIONS` | `gce_instance` |

### Cloud Logging
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_LOGGING_PROJECT_ID` | Project ID for logging | `AWS_CLOUDWATCH_LOG_GROUP` | `my-project-12345` |
| `GCP_LOGGING_LOG_NAME` | Log name | `AWS_CLOUDWATCH_LOG_STREAM` | `my-app-logs` |

## API Management Variables

### Apigee
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_APIGEE_ORGANIZATION` | Apigee organization name | `AWS_API_GATEWAY_REST_API_ID`, `AZURE_API_MANAGEMENT_SERVICE` | `my-org` |
| `GCP_APIGEE_ENVIRONMENT` | Apigee environment | `AWS_API_GATEWAY_STAGE` | `prod`, `dev` |
| `GCP_APIGEE_API_NAME` | API proxy name | `AWS_API_GATEWAY_API_NAME` | `my-api` |
| `GCP_APIGEE_BASE_URL` | Apigee base URL | `AWS_API_GATEWAY_ENDPOINT` | `https://my-org.apigee.net` |

## Container & Kubernetes Variables

### Google Kubernetes Engine (GKE)
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_GKE_CLUSTER_NAME` | GKE cluster name | `AWS_EKS_CLUSTER_NAME`, `AZURE_AKS_CLUSTER_NAME` | `my-cluster` |
| `GCP_GKE_CLUSTER_LOCATION` | Cluster location (region or zone) | `AWS_EKS_REGION` | `us-central1` |
| `GCP_GKE_NAMESPACE` | Kubernetes namespace | `AWS_EKS_NAMESPACE` | `default` |
| `GCP_GKE_NODE_POOL_NAME` | Node pool name | `AWS_EKS_NODE_GROUP` | `default-pool` |

## Authentication & Authorization Variables

### Service Accounts
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key file | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`, `AZURE_CLIENT_ID` + `AZURE_CLIENT_SECRET` | `/path/to/service-account.json` |
| `GCP_SERVICE_ACCOUNT_EMAIL` | Service account email | `AWS_IAM_ROLE_ARN` | `my-service@my-project.iam.gserviceaccount.com` |
| `GCP_SERVICE_ACCOUNT_KEY` | Service account key JSON (as string) | `AWS_SECRET_ACCESS_KEY` | `{"type": "service_account", ...}` |

## Networking Variables

| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_VPC_NETWORK_NAME` | VPC network name | `AWS_VPC_ID`, `AZURE_VNET_NAME` | `default` |
| `GCP_VPC_SUBNET_NAME` | Subnet name | `AWS_SUBNET_ID`, `AZURE_SUBNET_NAME` | `default` |
| `GCP_LOAD_BALANCER_IP` | Load balancer IP address | `AWS_ELB_DNS_NAME` | `1.2.3.4` |

## Caching Variables

### Memorystore (Redis)
| Variable Name | Description | AWS/Azure Equivalent | Example Value |
|--------------|-------------|---------------------|---------------|
| `GCP_MEMORYSTORE_REDIS_HOST` | Redis instance host | `AWS_ELASTICACHE_ENDPOINT`, `AZURE_REDIS_HOST` | `10.0.0.1` |
| `GCP_MEMORYSTORE_REDIS_PORT` | Redis port | `AWS_ELASTICACHE_PORT`, `AZURE_REDIS_PORT` | `6379` |
| `GCP_MEMORYSTORE_REDIS_INSTANCE_ID` | Redis instance ID | `AWS_ELASTICACHE_CLUSTER_ID` | `my-redis-instance` |

## Usage Examples

### Python Example
```python
import os
from google.cloud import storage

# Use GCP environment variables
project_id = os.getenv('GCP_PROJECT_ID', 'my-project-12345')
bucket_name = os.getenv('GCS_BUCKET_NAME', 'my-bucket')
region = os.getenv('GCP_REGION', 'us-central1')

# Initialize GCS client
client = storage.Client(project=project_id)
bucket = client.bucket(bucket_name)
blob = bucket.blob('data/file.txt')
blob.upload_from_filename('local_file.txt')
```

### Cloud Functions Example
```python
import os
import functions_framework
from google.cloud import pubsub_v1

# Use GCP environment variables
project_id = os.getenv('GCP_PROJECT_ID')
topic_id = os.getenv('GCP_PUBSUB_TOPIC_ID')

@functions_framework.http
def publish_message(request):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    future = publisher.publish(topic_path, b'Hello World!')
    return f'Message published: {future.result()}'
```

### Cloud SQL Example
```python
import os
from google.cloud.sql.connector import Connector
import pymysql

# Use GCP environment variables
connection_name = os.getenv('GCP_CLOUD_SQL_INSTANCE_CONNECTION_NAME')
db_user = os.getenv('GCP_CLOUD_SQL_USER')
db_password = os.getenv('GCP_CLOUD_SQL_PASSWORD')
db_name = os.getenv('GCP_CLOUD_SQL_DATABASE_NAME')

connector = Connector()
conn = connector.connect(
    connection_name,
    "pymysql",
    user=db_user,
    password=db_password,
    db=db_name
)
```

## Migration Mapping Reference

When migrating from AWS/Azure to GCP, use these mappings:

### AWS → GCP
- `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` → `GOOGLE_APPLICATION_CREDENTIALS`
- `AWS_REGION` → `GCP_REGION`
- `S3_BUCKET_NAME` → `GCS_BUCKET_NAME`
- `AWS_LAMBDA_FUNCTION_NAME` → `GCP_FUNCTION_NAME`
- `DYNAMODB_TABLE_NAME` → `GCP_FIRESTORE_COLLECTION_NAME`
- `SNS_TOPIC_ARN` / `SQS_QUEUE_URL` → `GCP_PUBSUB_TOPIC_ID`
- `RDS_ENDPOINT` → `GCP_CLOUD_SQL_INSTANCE_CONNECTION_NAME`

### Azure → GCP
- `AZURE_CLIENT_ID` + `AZURE_CLIENT_SECRET` → `GOOGLE_APPLICATION_CREDENTIALS`
- `AZURE_LOCATION` → `GCP_REGION`
- `AZURE_STORAGE_CONTAINER` → `GCS_BUCKET_NAME`
- `AZURE_FUNCTION_NAME` → `GCP_FUNCTION_NAME`
- `AZURE_COSMOS_DB_NAME` → `GCP_FIRESTORE_DATABASE_ID`
- `AZURE_SERVICE_BUS_TOPIC` → `GCP_PUBSUB_TOPIC_ID`
- `AZURE_SQL_SERVER` → `GCP_CLOUD_SQL_INSTANCE_CONNECTION_NAME`

## Best Practices

1. **Always use environment variables** - Never hardcode GCP project IDs, regions, or credentials
2. **Use consistent naming** - Follow the `GCP_` prefix convention for clarity
3. **Validate variables** - Check that required variables are set before using them
4. **Use default values carefully** - Only provide defaults for non-critical configuration
5. **Secure credentials** - Store `GOOGLE_APPLICATION_CREDENTIALS` securely, never commit to version control

## Validation Checklist

When refactoring code, ensure:
- [ ] All AWS/Azure variable references are replaced with GCP equivalents
- [ ] No hardcoded AWS/Azure service names remain in output code
- [ ] All GCP variables follow the naming convention (`GCP_` prefix)
- [ ] Environment variables are loaded from `os.getenv()` or similar
- [ ] No AWS/Azure SDK imports remain in refactored code
- [ ] All API calls use GCP client libraries
- [ ] Error handling uses GCP exception types
- [ ] Comments reference GCP services, not AWS/Azure
