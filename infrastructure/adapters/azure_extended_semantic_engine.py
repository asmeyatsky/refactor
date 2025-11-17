"""
Extended Semantic Refactoring Engine for Multiple Cloud Services (AWS & Azure)

This module extends the original semantic refactoring engine to handle
multiple cloud services and their GCP equivalents from both AWS and Azure.
"""

import ast
import re
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from infrastructure.adapters.service_mapping import ServiceMapper, ServiceMigrationMapping
from infrastructure.adapters.azure_mapping import AzureServiceMapper, AzureToGCPServiceMapping
from domain.value_objects import AWSService, GCPService, AzureService


class AzureExtendedASTTransformationEngine:
    """
    Extended Semantic Refactoring Engine supporting multiple cloud services
    
    Supports migration of various AWS and Azure services to their GCP equivalents.
    """
    
    def __init__(self):
        self.aws_service_mapper = ServiceMapper()
        self.azure_service_mapper = AzureServiceMapper()
        self.transformers = {
            'python': AzureExtendedPythonTransformer(self.aws_service_mapper, self.azure_service_mapper),
            'java': AzureExtendedJavaTransformer(self.aws_service_mapper, self.azure_service_mapper)  # Simplified implementation
        }
    
    def transform_code(self, code: str, language: str, transformation_recipe: Dict[str, Any]) -> str:
        """
        Transform code based on the transformation recipe
        """
        if language not in self.transformers:
            raise ValueError(f"Unsupported language: {language}")
        
        transformer = self.transformers[language]
        return transformer.transform(code, transformation_recipe)


class BaseAzureExtendedTransformer(ABC):
    """Base class for language-specific extended transformers"""
    
    def __init__(self, aws_service_mapper, azure_service_mapper):
        self.aws_service_mapper = aws_service_mapper
        self.azure_service_mapper = azure_service_mapper
    
    @abstractmethod
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform the code based on the recipe"""
        pass


class AzureExtendedPythonTransformer(BaseAzureExtendedTransformer):
    """Extended transformer for Python code using AST manipulation"""
    
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform Python code based on the recipe"""
        operation = recipe.get('operation', '')
        service_type = recipe.get('service_type', '')
        
        if operation == 'service_migration' and service_type:
            # Handle specific service migration based on service type
            if 'aws_s3_to_gcs' in service_type:
                return self._migrate_aws_s3_to_gcs(code)
            elif 'aws_lambda_to_cloud_functions' in service_type:
                return self._migrate_aws_lambda_to_cloud_functions(code)
            elif 'aws_dynamodb_to_firestore' in service_type:
                return self._migrate_aws_dynamodb_to_firestore(code)
            elif 'azure_blob_storage_to_gcs' in service_type:
                return self._migrate_azure_blob_storage_to_gcs(code)
            elif 'azure_functions_to_cloud_functions' in service_type:
                return self._migrate_azure_functions_to_cloud_functions(code)
            elif 'azure_cosmos_db_to_firestore' in service_type:
                return self._migrate_azure_cosmos_db_to_firestore(code)
            elif 'azure_service_bus_to_pubsub' in service_type:
                return self._migrate_azure_service_bus_to_pubsub(code)
            elif 'azure_event_hubs_to_pubsub' in service_type:
                return self._migrate_azure_event_hubs_to_pubsub(code)
            elif 'azure_sql_database_to_cloud_sql' in service_type:
                return self._migrate_azure_sql_database_to_cloud_sql(code)
            elif 'azure_virtual_machines_to_compute_engine' in service_type:
                return self._migrate_azure_virtual_machines_to_compute_engine(code)
            elif 'azure_monitor_to_monitoring' in service_type:
                return self._migrate_azure_monitor_to_monitoring(code)
            elif 'azure_api_management_to_apigee' in service_type:
                return self._migrate_azure_api_management_to_apigee(code)
            elif 'azure_redis_cache_to_memorystore' in service_type:
                return self._migrate_azure_redis_cache_to_memorystore(code)
            elif 'azure_aks_to_gke' in service_type:
                return self._migrate_azure_aks_to_gke(code)
            elif 'azure_container_instances_to_cloud_run' in service_type:
                return self._migrate_azure_container_instances_to_cloud_run(code)
            elif 'azure_app_service_to_cloud_run' in service_type:
                return self._migrate_azure_app_service_to_cloud_run(code)
        
        # If no specific service migration, try to detect and migrate automatically
        return self._auto_detect_and_migrate(code)
    
    def _auto_detect_and_migrate(self, code: str) -> str:
        """Automatically detect cloud services and migrate them"""
        result_code = code
        
        # Check for Azure services and apply transformations
        if 'azure.storage.blob' in result_code or 'BlobServiceClient' in result_code:
            result_code = self._migrate_azure_blob_storage_to_gcs(result_code)
        
        if 'azure.functions' in result_code or 'function_app' in result_code:
            result_code = self._migrate_azure_functions_to_cloud_functions(result_code)
        
        if 'azure.cosmos' in result_code or 'CosmosClient' in result_code:
            result_code = self._migrate_azure_cosmos_db_to_firestore(result_code)
        
        if 'azure.servicebus' in result_code or 'ServiceBusClient' in result_code:
            result_code = self._migrate_azure_service_bus_to_pubsub(result_code)
        
        if 'azure.eventhub' in result_code or 'EventHubProducerClient' in result_code:
            result_code = self._migrate_azure_event_hubs_to_pubsub(result_code)
        
        # Also check for AWS services and apply transformations
        if 'boto3' in result_code and 's3' in result_code.lower():
            result_code = self._migrate_aws_s3_to_gcs(result_code)
        
        if 'boto3' in result_code and 'lambda' in result_code.lower():
            result_code = self._migrate_aws_lambda_to_cloud_functions(result_code)
        
        if 'boto3' in result_code and 'dynamodb' in result_code.lower():
            result_code = self._migrate_aws_dynamodb_to_firestore(result_code)
        
        return result_code

    def _migrate_azure_blob_storage_to_gcs(self, code: str) -> str:
        """Migrate Azure Blob Storage to Google Cloud Storage"""
        # Replace Azure Blob Storage imports with GCS imports
        code = re.sub(r'from azure\.storage\.blob import.*', 'from google.cloud import storage', code)
        code = re.sub(r'import azure\.storage\.blob', 'from google.cloud import storage', code)
        
        # Replace client instantiation
        code = re.sub(
            r'BlobServiceClient\.from_connection_string\([^)]+\)',
            'storage.Client()',
            code
        )
        code = re.sub(
            r'BlobServiceClient\([^)]+account_url=([^,]+),\s*credential=([^)]+)\)',
            r'storage.Client()',
            code
        )
        
        # Replace blob operations with GCS equivalents
        code = re.sub(
            r'blob_client\.upload_blob\(([^)]+)\)',
            r'bucket = client.bucket("bucket_name")\n    blob = bucket.blob("blob_name")\n    blob.upload_from_string(\1)',
            code
        )
        
        code = re.sub(
            r'blob_client\.download_blob\(\)',
            r'content = blob.download_as_text()',
            code
        )
        
        return code
    
    def _migrate_azure_functions_to_cloud_functions(self, code: str) -> str:
        """Migrate Azure Functions to Google Cloud Functions"""
        # Replace Azure Functions imports
        code = re.sub(r'import azure\.functions as func', 'import functions_framework', code)
        
        # Replace function trigger patterns
        code = re.sub(
            r'@function_app\.route\([^)]+\)',
            '@functions_framework.http',
            code
        )
        code = re.sub(
            r'def main\(req: func\.HttpRequest\) -> func\.HttpResponse:',
            'def function_handler(request):',
            code
        )
        
        # Replace request/response handling
        code = re.sub(
            r'req\.get_json\(\)',
            'request.get_json()',
            code
        )
        code = re.sub(
            r'return func\.HttpResponse\([^)]+\)',
            'return "response"',
            code
        )
        
        return code

    def _migrate_azure_cosmos_db_to_firestore(self, code: str) -> str:
        """Migrate Azure Cosmos DB to Google Cloud Firestore"""
        # Replace Cosmos DB imports
        code = re.sub(r'from azure\.cosmos import.*', 'from google.cloud import firestore', code)
        
        # Replace client instantiation
        code = re.sub(
            r'CosmosClient\([^)]+url=([^,]+),\s*credential=([^)]+)\)',
            r'firestore.Client()',
            code
        )
        
        # Replace database operations
        code = re.sub(
            r'database\.get_container_client\(([^)]+)\)',
            r'db.collection(\1)',
            code
        )
        code = re.sub(
            r'container\.create_item\(([^)]+)\)',
            r'db.collection("collection").add(\1)',
            code
        )
        code = re.sub(
            r'container\.read_item\(([^)]+)\)',
            r'doc = db.collection("collection").document(\1)\n    doc.get()',
            code
        )
        
        return code
    
    def _migrate_azure_service_bus_to_pubsub(self, code: str) -> str:
        """Migrate Azure Service Bus to Google Cloud Pub/Sub"""
        # Replace Service Bus imports
        code = re.sub(r'from azure\.servicebus import.*', 'from google.cloud import pubsub_v1', code)
        
        # Replace client instantiation
        code = re.sub(
            r'ServiceBusClient\([^)]+conn_str=([^,]+),\s*queue_name=([^)]+)\)',
            r'publisher = pubsub_v1.PublisherClient()',
            code
        )
        
        # Replace message operations
        code = re.sub(
            r'message = ServiceBusMessage\(([^)]+)\)',
            r'data = \1.encode("utf-8")\n    future = publisher.publish(topic_path, data=data)',
            code
        )
        code = re.sub(
            r'sender\.send_messages\(message\)',
            r'future = publisher.publish(topic_path, data=data.encode("utf-8"))',
            code
        )
        
        return code
    
    def _migrate_azure_event_hubs_to_pubsub(self, code: str) -> str:
        """Migrate Azure Event Hubs to Google Cloud Pub/Sub"""
        # Replace Event Hubs imports
        code = re.sub(r'from azure\.eventhub import.*', 'from google.cloud import pubsub_v1', code)
        
        # Replace client instantiation
        code = re.sub(
            r'EventHubProducerClient\([^)]+\)',
            r'publisher = pubsub_v1.PublisherClient()',
            code
        )
        
        # Replace event operations
        code = re.sub(
            r'event_data_batch = producer\.create_batch\(\)',
            r'data = b"event_data"\n    future = publisher.publish(topic_path, data=data)',
            code
        )
        code = re.sub(
            r'producer\.send_batch\(event_data_batch\)',
            r'future = publisher.publish(topic_path, data=data)',
            code
        )
        
        return code
    
    def _migrate_azure_sql_database_to_cloud_sql(self, code: str) -> str:
        """Migrate Azure SQL Database to Google Cloud SQL"""
        # For simplicity, we'll show a basic migration of connection strings
        # A real implementation would involve using Cloud SQL Proxy or connectors
        
        # Replace connection handling
        code = re.sub(
            r'server=.*database\.windows\.net[^"]*',
            r'cloud_sql_connection = "project:region:instance"',
            code
        )
        
        # Replace pyodbc with Cloud SQL connector patterns
        code = re.sub(
            r'pyodbc\.connect\(([^)]+)\)',
            r'from google.cloud.sql.connector import Connector\n    with Connector() as connector:\n        conn = connector.connect("project:region:instance", "pyodbc", user="user", password="password", db="database")',
            code
        )
        
        return code
    
    def _migrate_azure_virtual_machines_to_compute_engine(self, code: str) -> str:
        """Migrate Azure Virtual Machines to Google Compute Engine"""
        # Replace imports
        code = re.sub(r'from azure\.mgmt\.compute import.*', 'from google.cloud import compute_v1', code)
        
        # Replace VM operations
        code = re.sub(
            r'compute_client\.virtual_machines\.',
            r'compute_v1.InstancesClient()',
            code
        )
        
        # Replace VM creation
        code = re.sub(
            r'parameters=VirtualMachine\([^)]+\)',
            r'instance = compute_v1.Instance(name="instance_name", machine_type="zones/zone/machineTypes/machine-type")',
            code
        )
        
        return code
    
    def _migrate_azure_monitor_to_monitoring(self, code: str) -> str:
        """Migrate Azure Monitor to Google Cloud Monitoring"""
        # Replace imports
        code = re.sub(r'from azure\.monitor\.query import.*', 'from google.cloud import monitoring_v3', code)
        
        # Replace monitoring operations
        code = re.sub(
            r'MetricsQueryClient\([^)]+\)',
            r'client = monitoring_v3.MetricServiceClient()',
            code
        )
        
        return code
    
    def _migrate_azure_api_management_to_apigee(self, code: str) -> str:
        """Migrate Azure API Management to Google Apigee"""
        # Replace imports
        code = re.sub(r'from azure\.mgmt\.apimanagement import.*', 'from apigee import apis, environments, proxy', code)
        
        # Replace API management operations
        code = re.sub(
            r'apim_client\.api\.',
            r'apis.create_api(',
            code
        )
        
        return code
    
    def _migrate_azure_redis_cache_to_memorystore(self, code: str) -> str:
        """Migrate Azure Redis Cache to Google Cloud Memorystore"""
        # Replace Redis imports (they are the same for both)
        # Focus on configuration differences
        
        # Replace Azure-specific Redis configurations
        code = re.sub(
            r'host=.*redis\.cache\.windows\.net',
            r'host = "project.region.cloud.redismemorystore.googleapis.com"',
            code
        )
        
        return code
    
    def _migrate_azure_aks_to_gke(self, code: str) -> str:
        """Migrate Azure Kubernetes Service to Google Kubernetes Engine"""
        # Replace imports
        code = re.sub(r'from azure\.mgmt\.containerservice import.*', 'from google.cloud import container_v1', code)
        
        # Replace cluster operations
        code = re.sub(
            r'container_service_client\.managed_clusters\.',
            r'container_v1.ClusterManagerClient()',
            code
        )
        
        return code
    
    def _migrate_azure_container_instances_to_cloud_run(self, code: str) -> str:
        """Migrate Azure Container Instances to Google Cloud Run"""
        # Replace imports
        code = re.sub(r'from azure\.mgmt\.containerinstance import.*', 'from google.cloud import run_v2', code)
        
        # Replace container operations
        code = re.sub(
            r'container_client\.container_groups\.',
            r'run_v2.ServicesClient()',
            code
        )
        
        return code
    
    def _migrate_azure_app_service_to_cloud_run(self, code: str) -> str:
        """Migrate Azure App Service to Google Cloud Run"""
        # Replace imports
        code = re.sub(r'from azure\.mgmt\.web import.*', 'from google.cloud import run_v2', code)
        
        # Replace app service operations
        code = re.sub(
            r'web_client\.webapps\.',
            r'run_v2.ServicesClient()',
            code
        )
        
        return code

    # AWS migration methods (from the original engine)
    def _migrate_aws_s3_to_gcs(self, code: str) -> str:
        """Migrate AWS S3 to Google Cloud Storage"""
        # Replace boto3 imports with GCS imports
        code = re.sub(r'import boto3', 'from google.cloud import storage', code)
        code = re.sub(r'from boto3', 'from google.cloud import storage', code)
        
        # Replace client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"].*\)',
            r'\1 = storage.Client()',
            code
        )
        
        # Replace S3 operations with GCS equivalents
        # put_object -> upload
        code = re.sub(
            r'(\w+)\.put_object\(Bucket=([^,]+), Key=([^,]+), Body=([^,\)]+)',
            r'bucket = \1.bucket(\2)\n    blob = bucket.blob(\3)\n    blob.upload_from_string(\4)',
            code
        )
        
        # get_object -> download
        code = re.sub(
            r'(\w+)\.get_object\(Bucket=([^,]+), Key=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blob = bucket.blob(\3)\n    content = blob.download_as_text()',
            code
        )
        
        # delete_object -> delete
        code = re.sub(
            r'(\w+)\.delete_object\(Bucket=([^,]+), Key=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blob = bucket.blob(\3)\n    blob.delete()',
            code
        )
        
        # list_objects -> list_blobs
        code = re.sub(
            r'(\w+)\.list_objects\(Bucket=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blobs = list(bucket.list_blobs())',
            code
        )
        
        return code

    def _migrate_aws_lambda_to_cloud_functions(self, code: str) -> str:
        """Migrate AWS Lambda to Google Cloud Functions"""
        # Replace Lambda client imports
        code = re.sub(r'import boto3', 'from google.cloud import functions_v1\nimport functions_framework', code)
        
        # Replace Lambda function decorator patterns
        code = re.sub(
            r'def lambda_handler\(event,\s*context\):',
            '@functions_framework.http\ndef function_handler(request):',
            code
        )
        
        # Replace Lambda invocation calls
        code = re.sub(
            r'lambda_client\.invoke\(FunctionName=([^,\)]+), Payload=([^,\)]+)\)',
            r'from google.cloud import functions_v1\nclient = functions_v1.CloudFunctionsServiceClient()\n# Manual invocation required',
            code
        )
        
        return code

    def _migrate_aws_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB to Google Cloud Firestore"""
        # Replace DynamoDB imports
        code = re.sub(r'import boto3', 'from google.cloud import firestore', code)
        
        # Replace DynamoDB client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]dynamodb[\'\"].*\)',
            r'\1 = firestore.Client()',
            code
        )
        
        # Replace table operations with collection/document operations
        code = re.sub(
            r'dynamodb\.put_item\(TableName=([^,]+), Item=([^,\)]+)\)',
            r'db.collection(\1).add(\2)',
            code
        )
        
        code = re.sub(
            r'dynamodb\.get_item\(TableName=([^,]+), Key=([^,\)]+)\)',
            r'doc = db.collection(\1).document(\2)\n    result = doc.get()',
            code
        )
        
        code = re.sub(
            r'dynamodb\.query\(TableName=([^,]+), KeyConditionExpression=([^,\)]+)\)',
            r'query = db.collection(\1).where(\2)\n    results = query.stream()',
            code
        )
        
        return code


class AzureExtendedJavaTransformer(BaseAzureExtendedTransformer):
    """Extended transformer for Java code (simplified implementation)"""
    
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform Java code based on the recipe"""
        # For Java, we would typically use JDT AST or similar, but this is a simplified version
        operation = recipe.get('operation', '')
        service_type = recipe.get('service_type', '')
        
        if operation == 'service_migration' and service_type:
            if service_type == 'azure_blob_storage_to_gcs':
                return self._migrate_azure_blob_storage_to_gcs(code)
            elif service_type == 'azure_functions_to_cloud_functions':
                return self._migrate_azure_functions_to_cloud_functions(code)
        
        return code
    
    def _migrate_azure_blob_storage_to_gcs(self, code: str) -> str:
        """Migrate Azure Blob Storage Java code to Google Cloud Storage"""
        # Replace Azure SDK imports with GCS imports
        code = re.sub(
            r'import com\.azure\.storage\.blob\..*;',
            'import com.google.cloud.storage.*;',
            code
        )
        
        return code
    
    def _migrate_azure_functions_to_cloud_functions(self, code: str) -> str:
        """Migrate Azure Functions Java code to Google Cloud Functions"""
        # Replace Azure Functions annotations
        code = re.sub(
            r'@FunctionName\(".*"\)',
            '@javax.annotation.Nullable',
            code
        )
        
        return code


class AzureExtendedSemanticRefactoringService:
    """
    Extended Service layer for semantic refactoring operations
    
    Orchestrates the refactoring process and applies transformations
    for multiple cloud services across AWS and Azure.
    """
    
    def __init__(self, ast_engine: AzureExtendedASTTransformationEngine):
        self.ast_engine = ast_engine
        self.azure_service_mapper = AzureServiceMapper()
        self.aws_service_mapper = ServiceMapper()
    
    def generate_transformation_recipe(self, source_code: str, target_api: str, language: str, service_type: str) -> Dict[str, Any]:
        """
        Generate a transformation recipe for refactoring code
        
        In a real implementation, an LLM would generate this based on the source
        code, target API, language, and service type.
        """
        recipe = {
            'language': language,
            'operation': 'service_migration',
            'service_type': service_type,
            'source_api': f'Azure {service_type.split("_to_")[0].replace("azure_", "").upper()}' if 'azure_' in service_type else f'AWS {service_type.split("_to_")[0].replace("aws_", "").upper()}',
            'target_api': target_api,
            'transformation_steps': [
                {
                    'step': 'replace_imports',
                    'pattern': 'Azure/AWS SDK imports',
                    'replacement': f'{target_api} SDK imports'
                },
                {
                    'step': 'replace_client_init',
                    'pattern': 'Azure/AWS client initialization',
                    'replacement': f'{target_api} client initialization'
                },
                {
                    'step': 'replace_api_calls',
                    'pattern': 'Azure/AWS API calls',
                    'replacement': f'{target_api} API calls'
                }
            ]
        }
        
        return recipe
    
    def apply_refactoring(self, source_code: str, language: str, service_type: str, target_api: str = None) -> str:
        """
        Apply refactoring to the source code for the specified service type
        """
        # If target API is not specified, infer it from the service type
        if not target_api:
            if 'azure_blob_storage_to_gcs' in service_type:
                target_api = 'GCS'
            elif 'azure_functions_to_cloud_functions' in service_type:
                target_api = 'Cloud Functions'
            elif 'azure_cosmos_db_to_firestore' in service_type:
                target_api = 'Firestore'
            elif 'azure_service_bus_to_pubsub' in service_type:
                target_api = 'Pub/Sub'
            elif 'azure_event_hubs_to_pubsub' in service_type:
                target_api = 'Pub/Sub'
            elif 'azure_sql_database_to_cloud_sql' in service_type:
                target_api = 'Cloud SQL'
            elif 'azure_monitor_to_monitoring' in service_type:
                target_api = 'Cloud Monitoring'
            elif 'azure_api_management_to_apigee' in service_type:
                target_api = 'Apigee'
            elif 'azure_redis_cache_to_memorystore' in service_type:
                target_api = 'Memorystore'
            elif 'azure_aks_to_gke' in service_type:
                target_api = 'GKE'
            elif 'azure_container_instances_to_cloud_run' in service_type:
                target_api = 'Cloud Run'
            elif 'azure_app_service_to_cloud_run' in service_type:
                target_api = 'Cloud Run'
            elif 'aws_s3_to_gcs' in service_type:
                target_api = 'GCS'
            elif 'aws_lambda_to_cloud_functions' in service_type:
                target_api = 'Cloud Functions'
            elif 'aws_dynamodb_to_firestore' in service_type:
                target_api = 'Firestore'
        
        # Generate transformation recipe
        recipe = self.generate_transformation_recipe(source_code, target_api, language, service_type)
        
        # Apply transformations using AST engine
        transformed_code = self.ast_engine.transform_code(source_code, language, recipe)
        
        return transformed_code
    
    def identify_and_migrate_services(self, source_code: str, language: str) -> Dict[str, str]:
        """
        Identify which cloud services are used in the code and migrate them
        """
        from infrastructure.adapters.service_mapping import ExtendedCodeAnalyzer
        code_analyzer = ExtendedCodeAnalyzer()
        services_found = code_analyzer.identify_all_cloud_services_usage(source_code)
        
        migrated_code = source_code
        migration_results = {}
        
        for service_key, matches in services_found.items():
            # Determine the service and provider
            if service_key.startswith('azure_'):
                # Process Azure services
                azure_service_name = service_key.replace('azure_', '')
                azure_service_enum = getattr(AzureService, azure_service_name.upper().replace('-', '_').replace(' ', '_'), None)
                
                if azure_service_enum and azure_service_enum in self.azure_service_mapper.get_all_mappings():
                    service_mapping = self.azure_service_mapper.get_mapping(azure_service_enum)
                    service_type = f"{service_key}_to_{service_mapping.gcp_service.value.replace('_', '-').lower()}"
                    
                    migrated_code = self.apply_refactoring(migrated_code, language, service_type)
                    migration_results[service_key] = {
                        'status': 'migrated',
                        'target_service': service_mapping.gcp_service.value,
                        'patterns_found': len(matches)
                    }
                else:
                    migration_results[service_key] = {
                        'status': 'not_supported',
                        'target_service': 'unknown',
                        'patterns_found': len(matches)
                    }
            
            elif service_key.startswith('aws_'):
                # Process AWS services
                aws_service_name = service_key.replace('aws_', '')
                aws_service_enum = getattr(AWSService, aws_service_name.upper().replace('-', '_'), None)
                
                if aws_service_enum and aws_service_enum in self.aws_service_mapper.get_all_mappings():
                    service_mapping = self.aws_service_mapper.get_mapping(aws_service_enum)
                    service_type = f"{service_key}_to_{service_mapping.gcp_service.value.replace('_', '-').lower()}"
                    
                    migrated_code = self.apply_refactoring(migrated_code, language, service_type)
                    migration_results[service_key] = {
                        'status': 'migrated',
                        'target_service': service_mapping.gcp_service.value,
                        'patterns_found': len(matches)
                    }
                else:
                    migration_results[service_key] = {
                        'status': 'not_supported',
                        'target_service': 'unknown',
                        'patterns_found': len(matches)
                    }
        
        return migration_results


def create_azure_extended_semantic_refactoring_engine() -> AzureExtendedSemanticRefactoringService:
    """Factory function to create an Azure extended semantic refactoring engine"""
    ast_engine = AzureExtendedASTTransformationEngine()
    return AzureExtendedSemanticRefactoringService(ast_engine)