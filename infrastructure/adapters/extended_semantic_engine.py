"""
Extended Semantic Refactoring Engine for Multiple AWS Services

This module extends the original semantic refactoring engine to handle
multiple AWS services and their GCP equivalents.
"""

import ast
import re
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from infrastructure.adapters.service_mapping import ServiceMapper, ServiceMigrationMapping, ExtendedCodeAnalyzer
from domain.value_objects import AWSService, GCPService


class ExtendedASTTransformationEngine:
    """
    Extended Semantic Refactoring Engine supporting multiple AWS services
    
    Supports migration of various AWS services to their GCP equivalents.
    """
    
    def __init__(self):
        self.service_mapper = ServiceMapper()
        self.transformers = {
            'python': ExtendedPythonTransformer(self.service_mapper),
            'java': ExtendedJavaTransformer(self.service_mapper)  # Simplified implementation
        }
    
    def transform_code(self, code: str, language: str, transformation_recipe: Dict[str, Any]) -> str:
        """
        Transform code based on the transformation recipe
        """
        if language not in self.transformers:
            raise ValueError(f"Unsupported language: {language}")
        
        transformer = self.transformers[language]
        return transformer.transform(code, transformation_recipe)


class BaseExtendedTransformer(ABC):
    """Base class for language-specific extended transformers"""
    
    def __init__(self, service_mapper):
        self.service_mapper = service_mapper
    
    @abstractmethod
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform the code based on the recipe"""
        pass


class ExtendedPythonTransformer(BaseExtendedTransformer):
    """Extended transformer for Python code using AST manipulation"""
    
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform Python code based on the recipe"""
        operation = recipe.get('operation', '')
        service_type = recipe.get('service_type', '')
        
        if operation == 'service_migration' and service_type:
            # Handle specific service migration
            if service_type == 's3_to_gcs':
                return self._migrate_s3_to_gcs(code)
            elif service_type == 'lambda_to_cloud_functions':
                return self._migrate_lambda_to_cloud_functions(code)
            elif service_type == 'dynamodb_to_firestore':
                return self._migrate_dynamodb_to_firestore(code)
            elif service_type == 'sqs_to_pubsub':
                return self._migrate_sqs_to_pubsub(code)
            elif service_type == 'sns_to_pubsub':
                return self._migrate_sns_to_pubsub(code)
            elif service_type == 'rds_to_cloud_sql':
                return self._migrate_rds_to_cloud_sql(code)
            elif service_type == 'cloudwatch_to_monitoring':
                return self._migrate_cloudwatch_to_monitoring(code)
            elif service_type == 'apigateway_to_apigee':
                return self._migrate_apigateway_to_apigee(code)
            elif service_type == 'eks_to_gke':
                return self._migrate_eks_to_gke(code)
            elif service_type == 'fargate_to_cloudrun':
                return self._migrate_fargate_to_cloudrun(code)

        # If no specific service migration, try to detect and migrate automatically
        return self._auto_detect_and_migrate(code)
    
    def _auto_detect_and_migrate(self, code: str) -> str:
        """Automatically detect AWS services and migrate them"""
        # This would analyze the code to identify which AWS services are being used
        # and apply appropriate transformations
        result_code = code
        
        # Check for each service type and apply transformations
        if 'boto3' in result_code and 's3' in result_code.lower():
            result_code = self._migrate_s3_to_gcs(result_code)
        
        if 'boto3' in result_code and 'lambda' in result_code.lower():
            result_code = self._migrate_lambda_to_cloud_functions(result_code)
        
        if 'boto3' in result_code and 'dynamodb' in result_code.lower():
            result_code = self._migrate_dynamodb_to_firestore(result_code)
        
        if 'boto3' in result_code and 'sqs' in result_code.lower():
            result_code = self._migrate_sqs_to_pubsub(result_code)
        
        if 'boto3' in result_code and 'sns' in result_code.lower():
            result_code = self._migrate_sns_to_pubsub(result_code)
        
        if 'boto3' in result_code and 'rds' in result_code.lower():
            result_code = self._migrate_rds_to_cloud_sql(result_code)
        
        if 'boto3' in result_code and 'cloudwatch' in result_code.lower():
            result_code = self._migrate_cloudwatch_to_monitoring(result_code)

        if 'boto3' in result_code and 'apigateway' in result_code.lower():
            result_code = self._migrate_apigateway_to_apigee(result_code)

        if 'boto3' in result_code and 'eks' in result_code.lower():
            result_code = self._migrate_eks_to_gke(result_code)

        if 'boto3' in result_code and ('ecs' in result_code.lower() or 'fargate' in result_code.lower()):
            result_code = self._migrate_fargate_to_cloudrun(result_code)

        return result_code
    
    def _migrate_s3_to_gcs(self, code: str) -> str:
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
    
    def _migrate_lambda_to_cloud_functions(self, code: str) -> str:
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
    
    def _migrate_dynamodb_to_firestore(self, code: str) -> str:
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
    
    def _migrate_sqs_to_pubsub(self, code: str) -> str:
        """Migrate AWS SQS to Google Cloud Pub/Sub"""
        # Replace SQS imports
        code = re.sub(r'import boto3', 'from google.cloud import pubsub_v1', code)
        
        # Replace SQS client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]sqs[\'\"].*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code
        )
        
        # Replace SQS operations with Pub/Sub operations
        code = re.sub(
            r'sqs\.send_message\(QueueUrl=([^,]+), MessageBody=([^,\)]+)\)',
            r'future = \1.publish(\2, data=\2.encode("utf-8"))',
            code
        )
        
        return code
    
    def _migrate_sns_to_pubsub(self, code: str) -> str:
        """Migrate AWS SNS to Google Cloud Pub/Sub"""
        # Replace SNS imports
        code = re.sub(r'import boto3', 'from google.cloud import pubsub_v1', code)
        
        # Replace SNS client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]sns[\'\"].*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code
        )
        
        # Replace SNS operations with Pub/Sub operations
        code = re.sub(
            r'sns\.publish\(TopicArn=([^,]+), Message=([^,\)]+)\)',
            r'future = \1.publish(\2, data=\2.encode("utf-8"))',
            code
        )
        
        return code
    
    def _migrate_rds_to_cloud_sql(self, code: str) -> str:
        """Migrate AWS RDS to Google Cloud SQL"""
        # Replace RDS imports
        if 'pymysql' in code:
            code = re.sub(r'import pymysql', 'from google.cloud.sql.connector import Connector\nimport pymysql', code)
        elif 'psycopg2' in code:
            code = re.sub(r'import psycopg2', 'from google.cloud.sql.connector import Connector\nimport psycopg2', code)
        
        # Replace connection patterns
        code = re.sub(
            r'connection = pymysql\.connect\(host=([^,]+), user=([^,]+), password=([^,]+), database=([^,\)]+)\)',
            r'with Connector() as connector:\n    connection = connector.connect(\n        "PROJECT:REGION:INSTANCE",\n        "pymysql",\n        user=\2,\n        password=\3,\n        db=\4\n    )',
            code
        )
        
        return code

    def _migrate_cloudwatch_to_monitoring(self, code: str) -> str:
        """Migrate AWS CloudWatch to Google Cloud Monitoring"""
        # Replace CloudWatch imports
        code = re.sub(r'import boto3', 'from google.cloud import monitoring_v3', code)

        # Replace CloudWatch client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]cloudwatch[\'\"].*\)',
            r'\1 = monitoring_v3.MetricServiceClient()',
            code
        )

        # Replace metric operations
        code = re.sub(
            r'cloudwatch\.put_metric_data\(Namespace=([^,]+), MetricData=\[([^,\)]+)\]\)',
            r'project_name = \1.project_path("PROJECT_ID")\n    # Metric data upload for monitoring_v3',
            code
        )

        return code

    def _migrate_apigateway_to_apigee(self, code: str) -> str:
        """Migrate AWS API Gateway to Apigee X"""
        # Replace API Gateway imports
        code = re.sub(r'import boto3', 'from apigee import apis, environments, proxy', code)

        # Replace API Gateway client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]apigateway[\'\"].*\)',
            r'\1 = apis.ApigeeAPI()',
            code
        )

        # Replace API creation operations
        code = re.sub(
            r'apigateway\.create_rest_api\(name=([^,\)]+)\)',
            r'result = apis.create_api(name=\1, type="apigee")',
            code
        )

        # Replace deployment operations
        code = re.sub(
            r'apigateway\.create_deployment\(restApiId=([^,]+), stageName=([^,\)]+)\)',
            r'proxy.deploy(api_id=\1, environment=\2)',
            code
        )

        return code

    def _migrate_eks_to_gke(self, code: str) -> str:
        """Migrate AWS EKS to Google Kubernetes Engine"""
        # Replace EKS imports
        code = re.sub(r'import boto3', 'from google.cloud import container_v1', code)

        # Replace EKS client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]eks[\'\"].*\)',
            r'\1 = container_v1.ClusterManagerClient()',
            code
        )

        # Replace cluster operations
        code = re.sub(
            r'eks\.create_cluster\(name=([^,]+), roleArn=([^,]+), resourcesVpcConfig=([^,\)]+)\)',
            r'parent = f"projects/{\1}/locations/-"\n    cluster = {\n        "name": \1,\n        "initial_node_count": 1,\n        "node_config": {"oauth_scopes": ["https://www.googleapis.com/auth/cloud-platform"]}\n    }\n    request = {"parent": parent, "cluster": cluster}\n    \1.create_cluster(request=request)',
            code
        )

        # Replace describe cluster
        code = re.sub(
            r'eks\.describe_cluster\(name=([^,\)]+)\)',
            r'request = {"name": f"projects/{\1}/locations/-/clusters/{\1}"}\n    response = \1.get_cluster(request=request)',
            code
        )

        # Replace delete cluster
        code = re.sub(
            r'eks\.delete_cluster\(name=([^,\)]+)\)',
            r'request = {"name": f"projects/{\1}/locations/-/clusters/{\1}"}\n    \1.delete_cluster(request=request)',
            code
        )

        return code

    def _migrate_fargate_to_cloudrun(self, code: str) -> str:
        """Migrate AWS Fargate (ECS) to Google Cloud Run"""
        # Replace ECS/Fargate imports (ECS manages Fargate tasks)
        code = re.sub(r'import boto3', 'from google.cloud import run_v2\nfrom google.cloud.run_v2.types import Service', code)

        # Replace ECS client instantiation (which handles Fargate)
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]ecs[\'\"].*\)',
            r'\1 = run_v2.ServicesClient()',
            code
        )

        # Replace ECS run_task which is used for Fargate
        code = re.sub(
            r'ecs\.run_task\(cluster=([^,]+), taskDefinition=([^,]+), count=([^,\)]+)\)',
            r'from google.cloud import run_v2\nfrom google.cloud.run_v2.types import Service\n\n# Convert to Cloud Run Job or Service\nparent = f"projects/{\1}/locations/-"\n# {\1} implementation for Cloud Run service',
            code
        )

        # Replace ECS register_task_definition
        code = re.sub(
            r'ecs\.register_task_definition\(family=([^,]+), containerDefinitions=([^,\)]+)\)',
            r'# Convert task definition to Cloud Run container configuration\n# {\1} container configuration for Cloud Run',
            code
        )

        # Replace ECS start_task
        code = re.sub(
            r'ecs\.start_task\(cluster=([^,]+), taskDefinition=([^,\)]+)\)',
            r'# Start Cloud Run job instead of ECS task\n# Use {\1} for Cloud Run execution',
            code
        )

        return code


class ExtendedJavaTransformer(BaseExtendedTransformer):
    """Extended transformer for Java code (simplified implementation)"""
    
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform Java code based on the recipe"""
        # For Java, we would typically use JDT AST or similar, but this is a simplified version
        operation = recipe.get('operation', '')
        service_type = recipe.get('service_type', '')
        
        if operation == 'service_migration' and service_type:
            if service_type == 's3_to_gcs':
                return self._migrate_s3_to_gcs(code)
            elif service_type == 'lambda_to_cloud_functions':
                return self._migrate_lambda_to_cloud_functions(code)
            elif service_type == 'dynamodb_to_firestore':
                return self._migrate_dynamodb_to_firestore(code)
        
        return code
    
    def _migrate_s3_to_gcs(self, code: str) -> str:
        """Migrate AWS S3 Java code to Google Cloud Storage"""
        # Replace AWS SDK imports with GCS imports
        code = re.sub(
            r'import com\.amazonaws\.services\.s3\..*;',
            'import com.google.cloud.storage.*;',
            code
        )
        
        # Replace S3 client instantiation
        code = re.sub(
            r'S3Client\.builder\(\).build\(\)',
            'StorageOptions.getDefaultInstance().getService()',
            code
        )
        
        return code
    
    def _migrate_lambda_to_cloud_functions(self, code: str) -> str:
        """Migrate AWS Lambda Java code to Google Cloud Functions"""
        # Replace Lambda imports
        code = re.sub(
            r'import com\.amazonaws\.services\.lambda\..*;',
            'import com.google.cloud.functions.*;',
            code
        )
        
        return code
    
    def _migrate_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB Java code to Google Cloud Firestore"""
        # Replace DynamoDB imports
        code = re.sub(
            r'import com\.amazonaws\.services\.dynamodbv2\..*;',
            'import com.google.cloud.firestore.*;',
            code
        )
        
        return code


class ExtendedSemanticRefactoringService:
    """
    Extended Service layer for semantic refactoring operations
    
    Orchestrates the refactoring process and applies transformations
    for multiple service types.
    """
    
    def __init__(self, ast_engine: ExtendedASTTransformationEngine):
        self.ast_engine = ast_engine
        self.service_mapper = ServiceMapper()
    
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
            'source_api': f'AWS {service_type.split("_to_")[0].upper()}',
            'target_api': target_api,
            'transformation_steps': [
                {
                    'step': 'replace_imports',
                    'pattern': f'AWS {service_type.split("_to_")[0].upper()} imports',
                    'replacement': f'{target_api} SDK imports'
                },
                {
                    'step': 'replace_client_init',
                    'pattern': f'AWS {service_type.split("_to_")[0].upper()} client initialization',
                    'replacement': f'{target_api} client initialization'
                },
                {
                    'step': 'replace_api_calls',
                    'pattern': f'AWS {service_type.split("_to_")[0].upper()} API calls',
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
            if service_type == 's3_to_gcs':
                target_api = 'GCS'
            elif service_type == 'lambda_to_cloud_functions':
                target_api = 'Cloud Functions'
            elif service_type == 'dynamodb_to_firestore':
                target_api = 'Firestore'
            elif service_type == 'sqs_to_pubsub':
                target_api = 'Pub/Sub'
            elif service_type == 'sns_to_pubsub':
                target_api = 'Pub/Sub'
            elif service_type == 'rds_to_cloud_sql':
                target_api = 'Cloud SQL'
            elif service_type == 'cloudwatch_to_monitoring':
                target_api = 'Cloud Monitoring'
        
        # Generate transformation recipe
        recipe = self.generate_transformation_recipe(source_code, target_api, language, service_type)
        
        # Apply transformations using AST engine
        transformed_code = self.ast_engine.transform_code(source_code, language, recipe)
        
        return transformed_code
    
    def identify_and_migrate_services(self, source_code: str, language: str) -> Dict[str, str]:
        """
        Identify which AWS services are used in the code and migrate them
        """
        code_analyzer = ExtendedCodeAnalyzer()
        services_found = code_analyzer.identify_aws_services_usage(source_code)
        
        migrated_code = source_code
        migration_results = {}
        
        for aws_service, matches in services_found.items():
            if aws_service in [AWSService.S3, AWSService.LAMBDA, AWSService.DYNAMODB, 
                             AWSService.SQS, AWSService.SNS, AWSService.RDS, AWSService.CLOUDWATCH]:
                
                service_mapping = self.service_mapper.get_mapping(aws_service)
                if service_mapping:
                    # Create service type string
                    service_type = f"{aws_service.value}_to_{service_mapping.gcp_service.value}"
                    service_type = service_type.replace('_', '-')
                    
                    migrated_code = self.apply_refactoring(migrated_code, language, service_type)
                    migration_results[aws_service.value] = {
                        'status': 'migrated',
                        'target_service': service_mapping.gcp_service.value,
                        'patterns_found': len(matches)
                    }
                else:
                    migration_results[aws_service.value] = {
                        'status': 'not_supported',
                        'target_service': 'unknown',
                        'patterns_found': len(matches)
                    }
        
        return migration_results


def create_extended_semantic_refactoring_engine() -> ExtendedSemanticRefactoringService:
    """Factory function to create an extended semantic refactoring engine"""
    ast_engine = ExtendedASTTransformationEngine()
    return ExtendedSemanticRefactoringService(ast_engine)