"""
Extended Cloud Refactor Agent - Service Mapping Support

This module extends the original agent to support multiple cloud services
with their GCP equivalents, including AWS and Azure services.
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Import from domain value objects
from domain.value_objects import AWSService, GCPService, AzureService
from infrastructure.adapters.azure_mapping import AzureToGCPServiceMapping, AzureServiceMapper


@dataclass
class ServiceMigrationMapping:
    """Mapping between AWS and GCP services for migration"""
    aws_service: AWSService
    gcp_service: GCPService
    aws_sdk_imports: List[str]
    gcp_sdk_imports: List[str]
    aws_api_patterns: List[str]
    gcp_api_patterns: List[str]
    auth_translation: Dict[str, str]
    config_translation: Dict[str, str]


class ServiceMapper:
    """Maps AWS services to their GCP equivalents"""
    
    SERVICE_MAPPINGS = {
        AWSService.S3: ServiceMigrationMapping(
            aws_service=AWSService.S3,
            gcp_service=GCPService.CLOUD_STORAGE,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.storage'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]s3[\'\"].*\)',
                r's3\.download_file',
                r's3\.upload_file',
                r's3\.put_object',
                r's3\.get_object',
                r's3\.list_objects',
                r's3\.delete_object'
            ],
            gcp_api_patterns=[
                r'storage\.Client\(\)',
                r'bucket\.download_to_filename',
                r'blob\.upload_from_filename',
                r'bucket\.blob',
                r'blob\.download_as_text'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_DEFAULT_REGION': 'GOOGLE_CLOUD_REGION'
            },
            config_translation={
                's3_endpoint': 'gcs_endpoint',
                's3_region': 'gcs_region'
            }
        ),
        
        AWSService.LAMBDA: ServiceMigrationMapping(
            aws_service=AWSService.LAMBDA,
            gcp_service=GCPService.CLOUD_FUNCTIONS,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.functions_v1', 'functions_framework'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]lambda[\'\"].*\)',
                r'lambda_client\.invoke',
                r'lambda_client\.create_function',
                r'lambda_client\.list_functions',
                r'lambda_client\.update_function_code',
                r'lambda_client\.get_function'
            ],
            gcp_api_patterns=[
                r'functions_v1\.CloudFunctionsServiceClient\(\)',
                r'@functions_framework\.http',
                r'@functions_framework\.cloud_event'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'lambda_role': 'gcp_service_account',
                'lambda_timeout': 'gcf_timeout',
                'handler': 'entry_point'
            }
        ),
        
        AWSService.DYNAMODB: ServiceMigrationMapping(
            aws_service=AWSService.DYNAMODB,
            gcp_service=GCPService.FIRESTORE,
            aws_sdk_imports=['boto3', 'pynamodb'],
            gcp_sdk_imports=['google.cloud.firestore'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]dynamodb[\'\"].*\)',
                r'dynamodb\.create_table',
                r'dynamodb\.put_item',
                r'dynamodb\.get_item',
                r'dynamodb\.query',
                r'dynamodb\.scan',
                r'dynamodb\.update_item',
                r'dynamodb\.delete_item'
            ],
            gcp_api_patterns=[
                r'db\.collection\(',
                r'db\.collection\(\w+\)\.document\(',
                r'doc\.get\(\)',
                r'doc\.set\(',
                r'doc\.update\(',
                r'doc\.delete\('
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'read_capacity_units': 'not_applicable',
                'write_capacity_units': 'not_applicable',
                'billing_mode': 'not_applicable'
            }
        ),
        
        AWSService.SQS: ServiceMigrationMapping(
            aws_service=AWSService.SQS,
            gcp_service=GCPService.PUB_SUB,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.pubsub'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]sqs[\'\"].*\)',
                r'sqs\.send_message',
                r'sqs\.receive_messages',
                r'sqs\.delete_message',
                r'sqs\.create_queue'
            ],
            gcp_api_patterns=[
                r'publisher\.',
                r'subscriber\.',
                r'publisher\.publish',
                r'subscriber\.subscribe'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'sqs_queue_name': 'pubsub_topic_name',
                'visibility_timeout': 'pubsub_ack_deadline'
            }
        ),
        
        AWSService.SNS: ServiceMigrationMapping(
            aws_service=AWSService.SNS,
            gcp_service=GCPService.PUB_SUB,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.pubsub'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]sns[\'\"].*\)',
                r'sns\.publish',
                r'sns\.create_topic',
                r'sns\.subscribe'
            ],
            gcp_api_patterns=[
                r'publisher\.publish',
                r'subscriber\.subscribe'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'sns_topic_arn': 'pubsub_topic_name',
                'sns_protocol': 'pubsub_protocol'
            }
        ),
        
        AWSService.RDS: ServiceMigrationMapping(
            aws_service=AWSService.RDS,
            gcp_service=GCPService.CLOUD_SQL,
            aws_sdk_imports=['boto3', 'pymysql', 'psycopg2'],
            gcp_sdk_imports=['google.cloud.sql.connector', 'PyMySQL', 'psycopg2'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]rds[\'\"].*\)',
                r'rds\.create_db_instance',
                r'rds\.delete_db_instance',
                r'rds\.describe_db_instances'
            ],
            gcp_api_patterns=[
                r'Connector\(\)',
                r'conn\.execute'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'db_instance_class': 'db_tier',
                'allocated_storage': 'db_size',
                'engine': 'db_engine'
            }
        ),
        
        AWSService.EC2: ServiceMigrationMapping(
            aws_service=AWSService.EC2,
            gcp_service=GCPService.COMPUTE_ENGINE,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.compute'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]ec2[\'\"].*\)',
                r'ec2\.run_instances',
                r'ec2\.terminate_instances',
                r'ec2\.describe_instances'
            ],
            gcp_api_patterns=[
                r'compute_v1\.InstancesClient\(\)',
                r'compute_v1\.instances_client'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'instance_type': 'machine_type',
                'ami_id': 'image',
                'security_group': 'firewall_rule'
            }
        ),
        
        AWSService.CLOUDWATCH: ServiceMigrationMapping(
            aws_service=AWSService.CLOUDWATCH,
            gcp_service=GCPService.CLOUD_MONITORING,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.monitoring'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]cloudwatch[\'\"].*\)',
                r'cloudwatch\.put_metric_data',
                r'cloudwatch\.get_metric_statistics'
            ],
            gcp_api_patterns=[
                r'metric_service_client\.',
                r'client\.create_time_series',
                r'client\.list_time_series'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'namespace': 'metric_type',
                'metric_name': 'metric_name'
            }
        ),

        AWSService.API_GATEWAY: ServiceMigrationMapping(
            aws_service=AWSService.API_GATEWAY,
            gcp_service=GCPService.CLOUD_ENDPOINTS,  # Placeholder - will change to Apigee
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['googleapiclient.discovery'],  # This would be different for Apigee
            aws_api_patterns=[
                r'boto3\.client\([\'\"]apigateway[\'\"].*\)',
                r'apigateway\.create_rest_api',
                r'apigateway\.create_resource',
                r'apigateway\.put_method',
                r'apigateway\.put_integration'
            ],
            gcp_api_patterns=[
                # These would be Apigee API patterns instead
                r'cloudendpoint.*',
                r'endpoints.*'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'api_name': 'apigee_api_name',
                'stage_name': 'apigee_environment',
                'rest_api_id': 'apigee_api_id'
            }
        ),

        AWSService.EKS: ServiceMigrationMapping(
            aws_service=AWSService.EKS,
            gcp_service=GCPService.GKE,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.container'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]eks[\'\"].*\)',
                r'eks\.create_cluster',
                r'eks\.describe_cluster',
                r'eks\.delete_cluster',
                r'eks\.list_clusters'
            ],
            gcp_api_patterns=[
                r'container\.ClusterManagerClient',
                r'client\.create_cluster',
                r'client\.get_cluster',
                r'client\.delete_cluster'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'cluster_name': 'gke_cluster_name',
                'role_arn': 'gke_service_account',
                'vpc_config': 'gke_network_config'
            }
        ),

        AWSService.FARGATE: ServiceMigrationMapping(
            aws_service=AWSService.FARGATE,
            gcp_service=GCPService.CLOUD_RUN,
            aws_sdk_imports=['boto3', 'botocore'],
            gcp_sdk_imports=['google.cloud.run_v2'],
            aws_api_patterns=[
                r'boto3\.client\([\'\"]ecs[\'\"].*\)',  # Fargate runs on ECS
                r'ecs\.run_task',
                r'ecs\.start_task',
                r'ecs\.register_task_definition'
            ],
            gcp_api_patterns=[
                r'run_v2\.ServicesClient',
                r'client\.create_service',
                r'client\.run_job'
            ],
            auth_translation={
                'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
                'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
            },
            config_translation={
                'task_definition': 'cloud_run_service',
                'cluster': 'cloud_run_location',
                'launch_type': 'execution_environment'
            }
        )
    }

    # Update the API Gateway mapping to use Apigee
    api_gateway_mapping = ServiceMigrationMapping(
        aws_service=AWSService.API_GATEWAY,
        gcp_service=GCPService.APIGEE,  # Now using the Apigee enum value
        aws_sdk_imports=['boto3', 'botocore'],
        gcp_sdk_imports=['apigee'],  # Using a generic apigee import pattern
        aws_api_patterns=[
            r'boto3\.client\([\'\"]apigateway[\'\"].*\)',
            r'apigateway\.create_rest_api',
            r'apigateway\.create_resource',
            r'apigateway\.put_method',
            r'apigateway\.put_integration'
        ],
        gcp_api_patterns=[
            r'apigee\.apis\.create',
            r'apigee\.apis\.deploy',
            r'apigee\.environments\.create',
            r'apigee\.proxy\.create'
        ],
        auth_translation={
            'AWS_ACCESS_KEY_ID': 'GOOGLE_APPLICATION_CREDENTIALS',
            'AWS_SECRET_ACCESS_KEY': 'GOOGLE_APPLICATION_CREDENTIALS'
        },
        config_translation={
            'api_name': 'apigee_api_name',
            'stage_name': 'apigee_environment',
            'rest_api_id': 'apigee_api_id'
        }
    )
    SERVICE_MAPPINGS[AWSService.API_GATEWAY] = api_gateway_mapping

    # Update the EKS mapping to use GKE (already added above in the main dictionary)
    
    @classmethod
    def get_mapping(cls, aws_service: AWSService) -> Optional[ServiceMigrationMapping]:
        """Get the migration mapping for an AWS service"""
        return cls.SERVICE_MAPPINGS.get(aws_service)
    
    @classmethod
    def get_all_mappings(cls) -> Dict[AWSService, ServiceMigrationMapping]:
        """Get all service mappings"""
        return cls.SERVICE_MAPPINGS
    
    @classmethod
    def get_aws_services(cls) -> List[AWSService]:
        """Get list of all supported AWS services"""
        return list(cls.SERVICE_MAPPINGS.keys())


class ExtendedCodeAnalyzer:
    """Extended code analyzer that can identify multiple cloud services"""

    def __init__(self):
        self.aws_service_mapper = ServiceMapper()
        self.azure_service_mapper = AzureServiceMapper()

    def identify_aws_services_usage(self, code_content: str) -> Dict[AWSService, List[str]]:
        """Identify which AWS services are used in the given code content"""
        services_found = {}

        for aws_service, mapping in self.aws_service_mapper.get_all_mappings().items():
            patterns = mapping.aws_api_patterns
            matches = []

            for pattern in patterns:
                import re
                matches.extend(re.findall(pattern, code_content, re.IGNORECASE))

            if matches:
                services_found[aws_service] = matches

        return services_found

    def identify_azure_services_usage(self, code_content: str) -> Dict[AzureService, List[str]]:
        """Identify which Azure services are used in the given code content"""
        services_found = {}

        for azure_service, mapping in self.azure_service_mapper.get_all_mappings().items():
            patterns = mapping.azure_api_patterns
            matches = []

            for pattern in patterns:
                import re
                matches.extend(re.findall(pattern, code_content, re.IGNORECASE))

            if matches:
                services_found[azure_service] = matches

        return services_found

    def identify_all_cloud_services_usage(self, code_content: str) -> Dict[str, List[str]]:
        """Identify all cloud services (AWS, Azure) used in the given code content"""
        all_services = {}

        # Check for AWS services
        aws_services = self.identify_aws_services_usage(code_content)
        for service, matches in aws_services.items():
            all_services[f"aws_{service.value}"] = matches

        # Check for Azure services
        azure_services = self.identify_azure_services_usage(code_content)
        for service, matches in azure_services.items():
            all_services[f"azure_{service.value}"] = matches

        return all_services


# Extended value objects for multi-service support
from domain.value_objects import MigrationType, ServiceMapping


def create_extended_service_mappings() -> List[ServiceMapping]:
    """Create extended service mappings for the domain layer"""
    extended_mappings = []
    
    for aws_service, mapping in ServiceMapper.SERVICE_MAPPINGS.items():
        service_mapping = ServiceMapping(
            source_service=aws_service.value,
            target_service=mapping.gcp_service.value,
            source_api_calls=mapping.aws_api_patterns,
            target_api_calls=mapping.gcp_api_patterns,
            authentication_mapping=mapping.auth_translation
        )
        extended_mappings.append(service_mapping)
    
    return extended_mappings