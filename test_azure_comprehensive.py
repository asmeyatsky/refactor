"""
Comprehensive Azure to GCP migration test suite
Tests all 15 Azure services with real-world code examples
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

# Comprehensive Azure Python test cases - Top 15 Services
AZURE_PYTHON_TESTS = {
    "blob_storage_basic": {
        "code": """from azure.storage.blob import BlobServiceClient
import os

connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Upload blob
container_client = blob_service_client.get_container_client("mycontainer")
blob_client = container_client.get_blob_client("myfile.txt")
with open("local_file.txt", "rb") as data:
    blob_client.upload_blob(data, overwrite=True)

# Download blob
download_stream = blob_client.download_blob()
with open("downloaded_file.txt", "wb") as download_file:
    download_file.write(download_stream.readall())

# List blobs
blobs = container_client.list_blobs()
for blob in blobs:
    print(f"Blob name: {blob.name}")
""",
        "services": ["blob_storage"],
        "expected": ["google.cloud.storage", "storage.Client", "bucket.blob", "upload_from_filename"],
        "forbidden": ["azure.storage.blob", "BlobServiceClient", "AZURE_STORAGE_CONNECTION_STRING"]
    },
    
    "blob_storage_sas_url": {
        "code": """from azure.storage.blob import BlobServiceClient, generate_container_sas
from azure.storage.blob import ContainerSasPermissions
from datetime import datetime, timedelta

blob_service_client = BlobServiceClient(account_url="https://mystorageaccount.blob.core.windows.net", credential="key")
container_client = blob_service_client.get_container_client("mycontainer")

# Generate SAS URL
sas_token = generate_container_sas(
    account_name="mystorageaccount",
    container_name="mycontainer",
    account_key="key",
    permission=ContainerSasPermissions(read=True),
    expiry=datetime.utcnow() + timedelta(hours=1)
)
sas_url = f"https://mystorageaccount.blob.core.windows.net/mycontainer?{sas_token}"
print(f"SAS URL: {sas_url}")
""",
        "services": ["blob_storage"],
        "expected": ["google.cloud.storage", "generate_signed_url"],
        "forbidden": ["azure.storage.blob", "generate_container_sas"]
    },
    
    "functions_http_trigger": {
        "code": """import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')
    
    if name:
        return func.HttpResponse(
            json.dumps({"message": f"Hello, {name}!"}),
            mimetype="application/json",
            status_code=200
        )
    else:
        return func.HttpResponse(
            "Please pass a name on the query string or in the request body",
            status_code=400
        )
""",
        "services": ["functions"],
        "expected": ["functions_framework", "@functions_framework.http", "def function"],
        "forbidden": ["azure.functions", "func.HttpRequest", "func.HttpResponse"]
    },
    
    "functions_blob_trigger": {
        "code": """import azure.functions as func
import logging

def main(myblob: func.InputStream):
    logging.info(f'Python blob trigger function processed blob \\n'
                f'Name: {myblob.name}\\n'
                f'Blob Size: {myblob.length} bytes')
    
    # Read blob content
    content = myblob.read()
    logging.info(f'Blob content: {content.decode("utf-8")}')
""",
        "services": ["functions"],
        "expected": ["functions_framework", "@functions_framework.cloud_event"],
        "forbidden": ["azure.functions", "func.InputStream"]
    },
    
    "cosmos_db_basic": {
        "code": """from azure.cosmos import CosmosClient, PartitionKey
import os

endpoint = os.getenv('COSMOS_ENDPOINT')
key = os.getenv('COSMOS_KEY')
client = CosmosClient(endpoint, key)

# Create database
database = client.create_database_if_not_exists(id='mydatabase')

# Create container
container = database.create_container_if_not_exists(
    id='mycontainer',
    partition_key=PartitionKey(path='/id')
)

# Create item
item = {
    'id': '1',
    'name': 'John Doe',
    'email': 'john@example.com'
}
container.create_item(body=item)

# Read item
item = container.read_item(item='1', partition_key='1')
print(f"Item: {item}")

# Query items
items = container.query_items(
    query='SELECT * FROM c WHERE c.name = @name',
    parameters=[{'name': '@name', 'value': 'John Doe'}]
)
for item in items:
    print(f"Found: {item}")
""",
        "services": ["cosmos_db"],
        "expected": ["google.cloud.firestore", "firestore.Client", "collection", "document", "set", "get"],
        "forbidden": ["azure.cosmos", "CosmosClient", "COSMOS_ENDPOINT", "COSMOS_KEY"]
    },
    
    "service_bus_queue": {
        "code": """from azure.servicebus import ServiceBusClient, ServiceBusMessage
import os

connection_string = os.getenv('SERVICEBUS_CONNECTION_STRING')
queue_name = "myqueue"

# Send message
with ServiceBusClient.from_connection_string(connection_string) as client:
    with client.get_queue_sender(queue_name) as sender:
        message = ServiceBusMessage("Hello, Service Bus!")
        sender.send_messages(message)

# Receive message
with ServiceBusClient.from_connection_string(connection_string) as client:
    with client.get_queue_receiver(queue_name) as receiver:
        received_messages = receiver.receive_messages(max_message_count=1)
        for msg in received_messages:
            print(f"Received: {msg}")
            receiver.complete_message(msg)
""",
        "services": ["service_bus"],
        "expected": ["google.cloud.pubsub_v1", "PublisherClient", "publish", "SubscriberClient"],
        "forbidden": ["azure.servicebus", "ServiceBusClient", "SERVICEBUS_CONNECTION_STRING"]
    },
    
    "service_bus_topic": {
        "code": """from azure.servicebus import ServiceBusClient, ServiceBusMessage

connection_string = "Endpoint=sb://..."
topic_name = "mytopic"
subscription_name = "mysubscription"

# Publish to topic
with ServiceBusClient.from_connection_string(connection_string) as client:
    with client.get_topic_sender(topic_name) as sender:
        message = ServiceBusMessage("Topic message")
        sender.send_messages(message)

# Subscribe from topic
with ServiceBusClient.from_connection_string(connection_string) as client:
    with client.get_subscription_receiver(topic_name, subscription_name) as receiver:
        received_messages = receiver.receive_messages(max_message_count=1)
        for msg in received_messages:
            print(f"Received: {msg}")
            receiver.complete_message(msg)
""",
        "services": ["service_bus"],
        "expected": ["google.cloud.pubsub_v1", "PublisherClient", "SubscriberClient"],
        "forbidden": ["azure.servicebus", "ServiceBusClient"]
    },
    
    "event_hubs_producer": {
        "code": """from azure.eventhub import EventHubProducerClient, EventData
import os

connection_string = os.getenv('EVENT_HUBS_CONNECTION_STRING')
eventhub_name = "myeventhub"

# Create producer
producer = EventHubProducerClient.from_connection_string(
    connection_string, 
    eventhub_name=eventhub_name
)

# Send events
event_data_batch = producer.create_batch()
event_data_batch.add(EventData('First event'))
event_data_batch.add(EventData('Second event'))
producer.send_batch(event_data_batch)
producer.close()
""",
        "services": ["event_hubs"],
        "expected": ["google.cloud.pubsub_v1", "PublisherClient", "publish"],
        "forbidden": ["azure.eventhub", "EventHubProducerClient", "EVENT_HUBS_CONNECTION_STRING"]
    },
    
    "event_hubs_consumer": {
        "code": """from azure.eventhub import EventHubConsumerClient
import os

connection_string = os.getenv('EVENT_HUBS_CONNECTION_STRING')
eventhub_name = "myeventhub"
consumer_group = "$Default"

def on_event(partition_context, event):
    print(f"Received event: {event.body_as_str()}")
    partition_context.update_checkpoint(event)

# Create consumer
consumer = EventHubConsumerClient.from_connection_string(
    connection_string,
    consumer_group=consumer_group,
    eventhub_name=eventhub_name
)

with consumer:
    consumer.receive(on_event=on_event, starting_position="-1")
""",
        "services": ["event_hubs"],
        "expected": ["google.cloud.pubsub_v1", "SubscriberClient", "subscribe"],
        "forbidden": ["azure.eventhub", "EventHubConsumerClient"]
    },
    
    "sql_database_pyodbc": {
        "code": """import pyodbc
import os

server = os.getenv('AZURE_SQL_SERVER')
database = os.getenv('AZURE_SQL_DATABASE')
username = os.getenv('AZURE_SQL_USERNAME')
password = os.getenv('AZURE_SQL_PASSWORD')

connection_string = (
    f"DRIVER={{ODBC Driver 17}}}}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password}"
)

conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

# Execute query
cursor.execute("SELECT * FROM Users WHERE id = ?", (1,))
row = cursor.fetchone()
print(f"User: {row}")

# Insert data
cursor.execute("INSERT INTO Users (name, email) VALUES (?, ?)", ("John", "john@example.com"))
conn.commit()
conn.close()
""",
        "services": ["sql_database"],
        "expected": ["google.cloud.sql.connector", "Connector", "connect"],
        "forbidden": ["pyodbc", "AZURE_SQL_SERVER", "AZURE_SQL_DATABASE"]
    },
    
    "virtual_machines": {
        "code": """from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
subscription_id = "your-subscription-id"
compute_client = ComputeManagementClient(credential, subscription_id)

# Create VM
vm_params = {
    'location': 'eastus',
    'hardware_profile': {
        'vm_size': 'Standard_D2s_v3'
    },
    'storage_profile': {
        'image_reference': {
            'publisher': 'Canonical',
            'offer': 'UbuntuServer',
            'sku': '18.04-LTS',
            'version': 'latest'
        }
    },
    'os_profile': {
        'computer_name': 'myvm',
        'admin_username': 'azureuser',
        'admin_password': 'Password123!'
    }
}

vm = compute_client.virtual_machines.create_or_update(
    'myresourcegroup',
    'myvm',
    vm_params
)
print(f"VM created: {vm.name}")
""",
        "services": ["virtual_machines"],
        "expected": ["google.cloud.compute_v1", "InstancesClient", "insert"],
        "forbidden": ["azure.mgmt.compute", "ComputeManagementClient"]
    },
    
    "monitor_metrics": {
        "code": """from azure.monitor.query import MetricsQueryClient
from azure.identity import DefaultAzureCredential
from datetime import timedelta

credential = DefaultAzureCredential()
client = MetricsQueryClient(credential)

resource_id = "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}"

# Query metrics
response = client.query_resource(
    resource_id,
    metric_names=["Percentage CPU"],
    timespan=timedelta(hours=1)
)

for metric in response.metrics:
    for time_series in metric.timeseries:
        for point in time_series.data:
            print(f"Timestamp: {point.time_stamp}, Value: {point.average}")
""",
        "services": ["monitor"],
        "expected": ["google.cloud.monitoring_v3", "MetricServiceClient", "query_time_series"],
        "forbidden": ["azure.monitor.query", "MetricsQueryClient"]
    },
    
    "api_management": {
        "code": """from azure.mgmt.apimanagement import ApiManagementClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
subscription_id = "your-subscription-id"
client = ApiManagementClient(credential, subscription_id)

# Create API
api_params = {
    'display_name': 'My API',
    'service_url': 'https://api.example.com',
    'path': 'myapi'
}

api = client.api.create_or_update(
    'myresourcegroup',
    'myapim',
    'myapi',
    api_params
)
print(f"API created: {api.display_name}")
""",
        "services": ["api_management"],
        "expected": ["apigee", "apis", "create_api"],
        "forbidden": ["azure.mgmt.apimanagement", "ApiManagementClient"]
    },
    
    "redis_cache": {
        "code": """import redis
import os

host = os.getenv('AZURE_REDIS_HOST')
port = os.getenv('AZURE_REDIS_PORT', 6380)
password = os.getenv('AZURE_REDIS_KEY')

# Connect to Redis
r = redis.StrictRedis(
    host=host,
    port=port,
    password=password,
    ssl=True,
    decode_responses=True
)

# Set and get
r.set('key', 'value')
value = r.get('key')
print(f"Value: {value}")

# List operations
r.lpush('mylist', 'item1', 'item2')
items = r.lrange('mylist', 0, -1)
print(f"List items: {items}")
""",
        "services": ["redis_cache"],
        "expected": ["google.cloud.redis_v1", "CloudRedisClient", "get_instance"],
        "forbidden": ["redis.StrictRedis", "AZURE_REDIS_HOST", "AZURE_REDIS_KEY"]
    },
    
    "aks_cluster": {
        "code": """from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.containerservice.models import ManagedCluster
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
subscription_id = "your-subscription-id"
client = ContainerServiceClient(credential, subscription_id)

# Create AKS cluster
cluster_params = ManagedCluster(
    location='eastus',
    dns_prefix='myaks',
    agent_pool_profiles=[{
        'name': 'agentpool',
        'count': 3,
        'vm_size': 'Standard_D2s_v3',
        'os_type': 'Linux'
    }],
    linux_profile={
        'admin_username': 'azureuser',
        'ssh': {
            'public_keys': [{
                'key_data': 'ssh-rsa ...'
            }]
        }
    }
)

cluster = client.managed_clusters.create_or_update(
    'myresourcegroup',
    'myaks',
    cluster_params
)
print(f"AKS cluster created: {cluster.name}")
""",
        "services": ["aks"],
        "expected": ["google.cloud.container_v1", "ClusterManagerClient", "create_cluster"],
        "forbidden": ["azure.mgmt.containerservice", "ContainerServiceClient"]
    },
    
    "container_instances": {
        "code": """from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import ContainerGroup, Container, ImageRegistryCredential
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
subscription_id = "your-subscription-id"
client = ContainerInstanceManagementClient(credential, subscription_id)

# Create container group
container_group = ContainerGroup(
    location='eastus',
    containers=[Container(
        name='mycontainer',
        image='nginx',
        resources={
            'requests': {
                'cpu': 1.0,
                'memory_in_gb': 1.5
            }
        }
    )],
    os_type='Linux'
)

group = client.container_groups.create_or_update(
    'myresourcegroup',
    'mycontainergroup',
    container_group
)
print(f"Container group created: {group.name}")
""",
        "services": ["container_instances"],
        "expected": ["google.cloud.run_v2", "ServicesClient", "create_service"],
        "forbidden": ["azure.mgmt.containerinstance", "ContainerInstanceManagementClient"]
    },
    
    "app_service": {
        "code": """from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import Site, SiteConfig
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
subscription_id = "your-subscription-id"
client = WebSiteManagementClient(credential, subscription_id)

# Create App Service
site_params = Site(
    location='eastus',
    site_config=SiteConfig(
        python_version='3.9',
        app_settings=[
            {'name': 'APP_SETTING', 'value': 'value'}
        ]
    )
)

site = client.web_apps.create_or_update(
    'myresourcegroup',
    'myappservice',
    site_params
)
print(f"App Service created: {site.name}")
""",
        "services": ["app_service"],
        "expected": ["google.cloud.run_v2", "ServicesClient", "create_service"],
        "forbidden": ["azure.mgmt.web", "WebSiteManagementClient"]
    },
    
    "key_vault_secrets": {
        "code": """from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

vault_url = "https://myvault.vault.azure.net/"
credential = DefaultAzureCredential()
client = SecretClient(vault_url=vault_url, credential=credential)

# Set secret
client.set_secret("my-secret", "my-secret-value")
print("Secret set")

# Get secret
secret = client.get_secret("my-secret")
print(f"Secret value: {secret.value}")

# List secrets
secrets = client.list_secrets()
for secret in secrets:
    print(f"Secret name: {secret.name}")

# Delete secret
client.delete_secret("my-secret")
print("Secret deleted")
""",
        "services": ["key_vault"],
        "expected": ["google.cloud.secretmanager", "SecretManagerServiceClient", "access_secret_version", "create_secret"],
        "forbidden": ["azure.keyvault.secrets", "SecretClient", "AZURE_KEY_VAULT_URL"]
    },
    
    "application_insights_telemetry": {
        "code": """from applicationinsights import TelemetryClient
from applicationinsights.logging import LoggingHandler
import logging

instrumentation_key = "your-instrumentation-key"
telemetry_client = TelemetryClient(instrumentation_key)

# Track event
telemetry_client.track_event("UserAction", {"user_id": "123", "action": "login"})

# Track exception
try:
    raise ValueError("Test exception")
except Exception as e:
    telemetry_client.track_exception(exception=e, properties={"severity": "high"})

# Track metric
telemetry_client.track_metric("ResponseTime", 150.5)

# Track trace
telemetry_client.track_trace("Processing started", severity_level="INFO")

# Flush telemetry
telemetry_client.flush()
""",
        "services": ["application_insights"],
        "expected": ["google.cloud.monitoring_v3", "google.cloud.logging", "log_struct", "log_text", "create_time_series"],
        "forbidden": ["applicationinsights", "TelemetryClient", "APPINSIGHTS_INSTRUMENTATION_KEY"]
    },
    
    "application_insights_logging": {
        "code": """from applicationinsights.logging import LoggingHandler
import logging

instrumentation_key = "your-instrumentation-key"
handler = LoggingHandler(instrumentation_key)

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Log messages
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred", exc_info=True)
""",
        "services": ["application_insights"],
        "expected": ["google.cloud.logging", "Client", "log_text"],
        "forbidden": ["applicationinsights.logging", "LoggingHandler"]
    },
    
    "multi_service_blob_cosmos": {
        "code": """from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
import os

# Blob Storage
blob_client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
container_client = blob_client.get_container_client("mycontainer")
blob_client_instance = container_client.get_blob_client("data.json")
data = blob_client_instance.download_blob().content_as_text()

# Cosmos DB
cosmos_client = CosmosClient(os.getenv('COSMOS_ENDPOINT'), os.getenv('COSMOS_KEY'))
database = cosmos_client.get_database_client('mydatabase')
container = database.get_container_client('mycontainer')

# Save to Cosmos DB
import json
item = json.loads(data)
container.create_item(body=item)
""",
        "services": ["blob_storage", "cosmos_db"],
        "expected": ["google.cloud.storage", "google.cloud.firestore", "storage.Client", "firestore.Client"],
        "forbidden": ["azure.storage.blob", "azure.cosmos", "BlobServiceClient", "CosmosClient"]
    },
    
    "multi_service_functions_keyvault": {
        "code": """import azure.functions as func
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Get secret from Key Vault
    vault_url = "https://myvault.vault.azure.net/"
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=vault_url, credential=credential)
    
    api_key = secret_client.get_secret("api-key").value
    
    return func.HttpResponse(f"API Key retrieved: {api_key[:5]}...")
""",
        "services": ["functions", "key_vault"],
        "expected": ["functions_framework", "google.cloud.secretmanager", "SecretManagerServiceClient"],
        "forbidden": ["azure.functions", "azure.keyvault.secrets", "func.HttpRequest"]
    }
}

# Azure C# test cases
AZURE_CSHARP_TESTS = {
    "blob_storage_csharp": {
        "code": """using Azure.Storage.Blobs;
using System;

var connectionString = Environment.GetEnvironmentVariable("AZURE_STORAGE_CONNECTION_STRING");
var blobServiceClient = new BlobServiceClient(connectionString);
var containerClient = blobServiceClient.GetBlobContainerClient("mycontainer");
var blobClient = containerClient.GetBlobClient("myfile.txt");

// Upload
using (var fileStream = System.IO.File.OpenRead("local_file.txt"))
{
    blobClient.Upload(fileStream, overwrite: true);
}

// Download
var downloadInfo = blobClient.Download();
using (var fileStream = System.IO.File.Create("downloaded_file.txt"))
{
    downloadInfo.Value.Content.CopyTo(fileStream);
}
""",
        "services": ["blob_storage"],
        "expected": ["Google.Cloud.Storage.V1", "StorageClient", "UploadObject"],
        "forbidden": ["Azure.Storage.Blobs", "BlobServiceClient"]
    },
    
    "key_vault_csharp": {
        "code": """using Azure.Security.KeyVault.Secrets;
using Azure.Identity;

var vaultUri = new Uri("https://myvault.vault.azure.net/");
var credential = new DefaultAzureCredential();
var client = new SecretClient(vaultUri, credential);

// Set secret
client.SetSecret("my-secret", "my-secret-value");

// Get secret
var secret = client.GetSecret("my-secret");
Console.WriteLine($"Secret value: {secret.Value.Value}");
""",
        "services": ["key_vault"],
        "expected": ["Google.Cloud.SecretManager.V1", "SecretManagerServiceClient", "AccessSecretVersion"],
        "forbidden": ["Azure.Security.KeyVault.Secrets", "SecretClient"]
    }
}


def test_migration(test_name: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single migration case"""
    print(f"\n{'='*70}")
    print(f"Testing: {test_name}")
    print(f"{'='*70}")
    
    try:
        # Submit migration request
        request_data = {
            "code": test_case["code"],
            "language": "python",
            "services": test_case["services"],
            "cloud_provider": "azure"
        }
        
        print(f"Services to migrate: {test_case['services']}")
        print(f"Submitting migration request...")
        
        response = requests.post(
            f"{BASE_URL}/api/migrate",
            json=request_data,
            timeout=300
        )
        
        if response.status_code != 200:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"API returned {response.status_code}: {response.text}"
            }
        
        migration_data = response.json()
        migration_id = migration_data["migration_id"]
        print(f"Migration ID: {migration_id}")
        
        # Poll for completion
        max_wait = 300  # 5 minutes
        wait_time = 0
        while wait_time < max_wait:
            status_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}")
            if status_response.status_code != 200:
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": f"Failed to get status: {status_response.status_code}"
                }
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "completed":
                print("✓ Migration completed")
                break
            elif status == "failed":
                error = status_data.get("result", {}).get("error", "Unknown error")
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": f"Migration failed: {error}"
                }
            
            time.sleep(2)
            wait_time += 2
            if wait_time % 10 == 0:
                print(f"  Waiting... ({wait_time}s)")
        
        if wait_time >= max_wait:
            return {
                "test_name": test_name,
                "success": False,
                "error": "Migration timed out"
            }
        
        # Get final result
        final_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}")
        final_data = final_response.json()
        
        refactored_code = final_data.get("refactored_code", "")
        validation = final_data.get("validation", {})
        
        if not refactored_code:
            return {
                "test_name": test_name,
                "success": False,
                "error": "No refactored code returned"
            }
        
        print(f"\nRefactored code preview (first 500 chars):")
        print("-" * 70)
        print(refactored_code[:500])
        print("-" * 70)
        
        # Validate results
        result = {
            "test_name": test_name,
            "success": True,
            "refactored_code_length": len(refactored_code),
            "validation": validation
        }
        
        # Check for expected patterns
        missing = []
        for pattern in test_case.get("expected", []):
            if pattern.lower() not in refactored_code.lower():
                missing.append(pattern)
                print(f"✗ Missing expected pattern: {pattern}")
        
        if missing:
            result["missing_patterns"] = missing
            result["success"] = False
        
        # Check for forbidden patterns
        found_forbidden = []
        for pattern in test_case.get("forbidden", []):
            if pattern.lower() in refactored_code.lower():
                found_forbidden.append(pattern)
                print(f"✗ Found forbidden pattern: {pattern}")
        
        if found_forbidden:
            result["forbidden_patterns"] = found_forbidden
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
    """Run all Azure to GCP migration tests"""
    print("="*70)
    print("COMPREHENSIVE AZURE TO GCP MIGRATION TEST SUITE")
    print("Testing all 15 Azure Services")
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
    
    # Test Azure Python services
    print("\n" + "="*70)
    print("TESTING AZURE PYTHON SERVICE MIGRATIONS (All 15 Services)")
    print("="*70)
    for test_name, test_case in AZURE_PYTHON_TESTS.items():
        result = test_migration(f"azure_python_{test_name}", test_case)
        results.append(result)
        time.sleep(1)  # Rate limiting
    
    # Test Azure C# services
    print("\n" + "="*70)
    print("TESTING AZURE C# SERVICE MIGRATIONS")
    print("="*70)
    for test_name, test_case in AZURE_CSHARP_TESTS.items():
        # Update language for C# tests
        test_case_copy = test_case.copy()
        test_case_copy["language"] = "csharp"
        result = test_migration(f"azure_csharp_{test_name}", test_case_copy)
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
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    
    # Service breakdown
    service_results = {}
    for result in results:
        test_name = result.get("test_name", "")
        for service in ["blob_storage", "functions", "cosmos_db", "service_bus", "event_hubs",
                       "sql_database", "virtual_machines", "monitor", "api_management",
                       "redis_cache", "aks", "container_instances", "app_service",
                       "key_vault", "application_insights"]:
            if service in test_name:
                if service not in service_results:
                    service_results[service] = {"passed": 0, "failed": 0}
                if result.get("success", False):
                    service_results[service]["passed"] += 1
                else:
                    service_results[service]["failed"] += 1
    
    print("\nService Breakdown:")
    for service, counts in sorted(service_results.items()):
        total_service = counts["passed"] + counts["failed"]
        print(f"  {service}: {counts['passed']}/{total_service} passed")
    
    if failed > 0:
        print("\nFailed tests:")
        for result in results:
            if not result.get("success", False):
                error = result.get("error", "Unknown error")
                missing = result.get("missing_patterns", [])
                forbidden = result.get("forbidden_patterns", [])
                print(f"  ✗ {result['test_name']}")
                if error:
                    print(f"    Error: {error}")
                if missing:
                    print(f"    Missing patterns: {missing}")
                if forbidden:
                    print(f"    Forbidden patterns: {forbidden}")
    
    # Save detailed results
    with open("test_azure_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to test_azure_results.json")
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if all(r.get("success", False) for r in results) else 1)
