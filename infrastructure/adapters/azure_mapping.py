"""
Azure to GCP Service Mapping Support

This module adds Azure-specific service mappings for the Cloud Refactor Agent,
extending it to support Azure to GCP migrations in addition to AWS to GCP.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

from domain.value_objects import AzureService, GCPService


@dataclass
class AzureToGCPServiceMapping:
    """Mapping between Azure and GCP services for migration"""
    azure_service: AzureService
    gcp_service: GCPService
    azure_sdk_imports: List[str]
    gcp_sdk_imports: List[str]
    azure_api_patterns: List[str]
    gcp_api_patterns: List[str]
    auth_translation: Dict[str, str]
    config_translation: Dict[str, str]


class AzureServiceMapper:
    """Maps Azure services to their GCP equivalents"""
    
    SERVICE_MAPPINGS = {
        AzureService.BLOB_STORAGE: AzureToGCPServiceMapping(
            azure_service=AzureService.BLOB_STORAGE,
            gcp_service=GCPService.CLOUD_STORAGE,
            azure_sdk_imports=['azure.storage.blob'],
            gcp_sdk_imports=['google.cloud.storage'],
            azure_api_patterns=[
                r'BlobServiceClient',
                r'blob_client\.',
                r'container_client\.',
                r'upload_blob',
                r'download_blob'
            ],
            gcp_api_patterns=[
                r'storage\.Client\(',
                r'bucket\.blob',
                r'blob\.upload_from',
                r'blob\.download_'
            ],
            auth_translation={
                'AZURE_STORAGE_ACCOUNT_NAME': 'GOOGLE_CLOUD_PROJECT',
                'AZURE_STORAGE_ACCOUNT_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'storage_account': 'bucket_name',
                'container_name': 'gcs_bucket'
            }
        ),
        
        AzureService.FUNCTIONS: AzureToGCPServiceMapping(
            azure_service=AzureService.FUNCTIONS,
            gcp_service=GCPService.CLOUD_FUNCTIONS,
            azure_sdk_imports=['azure.functions'],
            gcp_sdk_imports=['functions_framework'],
            azure_api_patterns=[
                r'@function_app',
                r'def main\(',
                r'func\.HttpRequest',
                r'func\.Out'
            ],
            gcp_api_patterns=[
                r'@functions_framework\.',
                r'def function\(',
                r'request\.json',
                r'return.*json'
            ],
            auth_translation={
                'AzureWebJobsStorage': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'function_name': 'gcf_function_name',
                'trigger': 'gcf_trigger'
            }
        ),
        
        AzureService.COSMOS_DB: AzureToGCPServiceMapping(
            azure_service=AzureService.COSMOS_DB,
            gcp_service=GCPService.FIRESTORE,
            azure_sdk_imports=['azure.cosmos'],
            gcp_sdk_imports=['google.cloud.firestore'],
            azure_api_patterns=[
                r'CosmosClient',
                r'database\.',
                r'container\.',
                r'create_item',
                r'read_item'
            ],
            gcp_api_patterns=[
                r'firestore\.Client\(',
                r'collection\(',
                r'document\(',
                r'doc\.set',
                r'doc\.get'
            ],
            auth_translation={
                'COSMOS_ENDPOINT': 'GOOGLE_CLOUD_PROJECT',
                'COSMOS_MASTER_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'database_id': 'firestore_project',
                'container_id': 'collection_name'
            }
        ),
        
        AzureService.SERVICE_BUS: AzureToGCPServiceMapping(
            azure_service=AzureService.SERVICE_BUS,
            gcp_service=GCPService.PUB_SUB,
            azure_sdk_imports=['azure.servicebus'],
            gcp_sdk_imports=['google.cloud.pubsub'],
            azure_api_patterns=[
                r'ServiceBusClient',
                r'QueueClient',
                r'TopicClient',
                r'sender\.',
                r'receiver\.'
            ],
            gcp_api_patterns=[
                r'publisher\.',
                r'subscriber\.',
                r'pubsub_v1\.'
            ],
            auth_translation={
                'SERVICEBUS_CONNECTION_STRING': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'queue_name': 'pubsub_topic',
                'topic_name': 'pubsub_topic'
            }
        ),
        
        AzureService.EVENT_HUBS: AzureToGCPServiceMapping(
            azure_service=AzureService.EVENT_HUBS,
            gcp_service=GCPService.PUB_SUB,
            azure_sdk_imports=['azure.eventhub'],
            gcp_sdk_imports=['google.cloud.pubsub'],
            azure_api_patterns=[
                r'EventHubProducerClient',
                r'EventHubConsumerClient',
                r'sender\.',
                r'receiver\.'
            ],
            gcp_api_patterns=[
                r'publisher\.',
                r'subscriber\.',
                r'pubsub_v1\.'
            ],
            auth_translation={
                'EVENT_HUBS_CONNECTION_STRING': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'eventhub_name': 'pubsub_topic',
                'consumer_group': 'pubsub_subscription'
            }
        ),
        
        AzureService.SQL_DATABASE: AzureToGCPServiceMapping(
            azure_service=AzureService.SQL_DATABASE,
            gcp_service=GCPService.CLOUD_SQL,
            azure_sdk_imports=['pyodbc', 'pymssql'],
            gcp_sdk_imports=['google.cloud.sql.connector', 'PyMySQL', 'psycopg2'],
            azure_api_patterns=[
                r'server=.*database\.windows\.net',
                r'driver=.*ODBC Driver'
            ],
            gcp_api_patterns=[
                r'Connector\(',
                r'conn\.execute'
            ],
            auth_translation={
                'AZURE_SQL_SERVER': 'GOOGLE_CLOUD_SQL_INSTANCE'
            },
            config_translation={
                'database': 'cloud_sql_database',
                'server': 'cloud_sql_connection_name'
            }
        ),
        
        AzureService.VIRTUAL_MACHINES: AzureToGCPServiceMapping(
            azure_service=AzureService.VIRTUAL_MACHINES,
            gcp_service=GCPService.COMPUTE_ENGINE,
            azure_sdk_imports=['azure.mgmt.compute'],
            gcp_sdk_imports=['google.cloud.compute_v1'],
            azure_api_patterns=[
                r'ComputeManagementClient',
                r'virtual_machines\.',
                r'vm_sizes\.',
                r'create_or_update'
            ],
            gcp_api_patterns=[
                r'compute_v1\.InstancesClient\(',
                r'insert\(',
                r'get\('
            ],
            auth_translation={
                'AZURE_CLIENT_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AZURE_CLIENT_SECRET': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'vm_size': 'machine_type',
                'storage_account_type': 'disk_type'
            }
        ),
        
        AzureService.MONITOR: AzureToGCPServiceMapping(
            azure_service=AzureService.MONITOR,
            gcp_service=GCPService.CLOUD_MONITORING,
            azure_sdk_imports=['azure.monitor.query'],
            gcp_sdk_imports=['google.cloud.monitoring_v3'],
            azure_api_patterns=[
                r'MetricsQueryClient',
                r'logs_query_client',
                r'execute_query'
            ],
            gcp_api_patterns=[
                r'metric_service_client\.',
                r'query\('
            ],
            auth_translation={
                'AZURE_LOG_ANALYTICS_WORKSPACE_ID': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'workspace_id': 'project_id',
                'metric_namespace': 'metric_type'
            }
        ),
        
        AzureService.API_MANAGEMENT: AzureToGCPServiceMapping(
            azure_service=AzureService.API_MANAGEMENT,
            gcp_service=GCPService.APIGEE,
            azure_sdk_imports=['azure.mgmt.apimanagement'],
            gcp_sdk_imports=['apigee'],
            azure_api_patterns=[
                r'ApiManagementClient',
                r'api_management\.',
                r'apis\.',
                r'operations\.'
            ],
            gcp_api_patterns=[
                r'apigee\.apis\.',
                r'create_api',
                r'deploy'
            ],
            auth_translation={
                'AZURE_SUBSCRIPTION_ID': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'api_id': 'apigee_api_name',
                'resource_group': 'gcp_region'
            }
        ),
        
        AzureService.REDIS_CACHE: AzureToGCPServiceMapping(
            azure_service=AzureService.REDIS_CACHE,
            gcp_service=GCPService.MEMORYSTORE,
            azure_sdk_imports=['redis'],
            gcp_sdk_imports=['google.cloud.redis_v1'],
            azure_api_patterns=[
                r'redis\.StrictRedis\(',
                r'redis\.Redis\(',
                r'r\.get\(',
                r'r\.set\('
            ],
            gcp_api_patterns=[
                r'redis_v1\.CloudRedisClient\(',
                r'get_instance\(',
                r'create_instance\('
            ],
            auth_translation={
                'AZURE_REDIS_HOST': 'GOOGLE_CLOUD_PROJECT',
                'AZURE_REDIS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'host': 'memorystore_instance',
                'port': 'memorystore_port'
            }
        ),
        
        AzureService.AKS: AzureToGCPServiceMapping(
            azure_service=AzureService.AKS,
            gcp_service=GCPService.GKE,
            azure_sdk_imports=['azure.mgmt.containerservice'],
            gcp_sdk_imports=['google.cloud.container_v1'],
            azure_api_patterns=[
                r'ContainerServiceClient',
                r'managed_clusters\.',
                r'create_or_update'
            ],
            gcp_api_patterns=[
                r'container_v1\.ClusterManagerClient\(',
                r'create_cluster\(',
                r'get_cluster\('
            ],
            auth_translation={
                'AZURE_SUBSCRIPTION_ID': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'agent_pool_profiles': 'node_config',
                'kubernetes_version': 'initial_cluster_version'
            }
        ),
        
        AzureService.CONTAINER_INSTANCES: AzureToGCPServiceMapping(
            azure_service=AzureService.CONTAINER_INSTANCES,
            gcp_service=GCPService.CLOUD_RUN,
            azure_sdk_imports=['azure.mgmt.containerinstance'],
            gcp_sdk_imports=['google.cloud.run_v2'],
            azure_api_patterns=[
                r'ContainerInstanceManagementClient',
                r'container_groups\.',
                r'containers\.',
                r'create_or_update'
            ],
            gcp_api_patterns=[
                r'run_v2\.ServicesClient\(',
                r'create_service\(',
                r'get_service\('
            ],
            auth_translation={
                'AZURE_SUBSCRIPTION_ID': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'containers': 'container_config',
                'os_type': 'execution_environment'
            }
        ),
        
        AzureService.APP_SERVICE: AzureToGCPServiceMapping(
            azure_service=AzureService.APP_SERVICE,
            gcp_service=GCPService.CLOUD_RUN,
            azure_sdk_imports=['azure.mgmt.web'],
            gcp_sdk_imports=['google.cloud.run_v2'],
            azure_api_patterns=[
                r'WebSiteManagementClient',
                r'webapps\.',
                r'create_or_update',
                r'deploy'
            ],
            gcp_api_patterns=[
                r'run_v2\.ServicesClient\(',
                r'create_service\(',
                r'deploy_service\('
            ],
            auth_translation={
                'AZURE_SUBSCRIPTION_ID': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'app_service_plan': 'cloud_run_service',
                'site_name': 'service_name'
            }
        ),
        
        AzureService.KEY_VAULT: AzureToGCPServiceMapping(
            azure_service=AzureService.KEY_VAULT,
            gcp_service=GCPService.SECRET_MANAGER,
            azure_sdk_imports=['azure.keyvault.secrets', 'azure.identity'],
            gcp_sdk_imports=['google.cloud.secretmanager'],
            azure_api_patterns=[
                r'SecretClient',
                r'KeyVaultClient',
                r'get_secret',
                r'set_secret',
                r'delete_secret',
                r'list_secrets'
            ],
            gcp_api_patterns=[
                r'secretmanager\.SecretManagerServiceClient\(',
                r'access_secret_version',
                r'create_secret',
                r'delete_secret',
                r'list_secrets'
            ],
            auth_translation={
                'AZURE_KEY_VAULT_URL': 'GOOGLE_CLOUD_PROJECT',
                'AZURE_CLIENT_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AZURE_CLIENT_SECRET': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AZURE_TENANT_ID': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'vault_url': 'project_id',
                'secret_name': 'secret_id',
                'secret_version': 'version_id'
            }
        ),
        
        AzureService.APPLICATION_INSIGHTS: AzureToGCPServiceMapping(
            azure_service=AzureService.APPLICATION_INSIGHTS,
            gcp_service=GCPService.CLOUD_MONITORING,
            azure_sdk_imports=['azure.applicationinsights', 'applicationinsights'],
            gcp_sdk_imports=['google.cloud.monitoring_v3', 'google.cloud.logging'],
            azure_api_patterns=[
                r'ApplicationInsightsClient',
                r'TelemetryClient',
                r'track_event',
                r'track_exception',
                r'track_metric',
                r'track_trace',
                r'flush'
            ],
            gcp_api_patterns=[
                r'monitoring_v3\.MetricServiceClient\(',
                r'logging\.Client\(',
                r'create_time_series',
                r'log_text',
                r'log_struct'
            ],
            auth_translation={
                'APPINSIGHTS_INSTRUMENTATION_KEY': 'GOOGLE_CLOUD_PROJECT',
                'APPINSIGHTS_CONNECTION_STRING': 'GOOGLE_CLOUD_PROJECT'
            },
            config_translation={
                'instrumentation_key': 'project_id',
                'connection_string': 'project_id',
                'app_id': 'project_id'
            }
        )
    }
    
    @classmethod
    def get_mapping(cls, azure_service: AzureService) -> Optional[AzureToGCPServiceMapping]:
        """Get the migration mapping for an Azure service"""
        return cls.SERVICE_MAPPINGS.get(azure_service)
    
    @classmethod
    def get_all_mappings(cls) -> Dict[AzureService, AzureToGCPServiceMapping]:
        """Get all Azure to GCP service mappings"""
        return cls.SERVICE_MAPPINGS
    
    @classmethod
    def get_azure_services(cls) -> List[AzureService]:
        """Get list of all supported Azure services"""
        return list(cls.SERVICE_MAPPINGS.keys())


# Extended service mapping to include cloud provider information
@dataclass
class ExtendedServiceMapping:
    """Extended service mapping with cloud provider information"""
    source_provider: str  # 'aws', 'azure', 'gcp'
    source_service: str
    target_provider: str  # 'aws', 'azure', 'gcp'
    target_service: str
    source_api_calls: List[str]
    target_api_calls: List[str]
    authentication_mapping: dict
    config_mapping: dict = None
    source_sdk_imports: List[str] = None
    target_sdk_imports: List[str] = None