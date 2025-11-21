"""
Infrastructure as Code (IaC) Detector

Architectural Intent:
- Detects Infrastructure as Code files across repositories
- Identifies cloud services referenced in IaC files
- Supports Terraform, CloudFormation, Pulumi, and Kubernetes manifests
"""

import os
import re
import json
import yaml
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum


class IACType(Enum):
    """Types of Infrastructure as Code"""
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    PULUMI = "pulumi"
    KUBERNETES = "kubernetes"
    DOCKER_COMPOSE = "docker_compose"
    ANSIBLE = "ansible"
    UNKNOWN = "unknown"


@dataclass
class IACFile:
    """Represents an Infrastructure as Code file"""
    file_path: str
    iac_type: IACType
    services_referenced: List[str]  # AWS/Azure services found
    gcp_services_mapped: Dict[str, str]  # Mapping of detected services to GCP equivalents
    estimated_changes: int
    complexity: str  # 'simple', 'moderate', 'complex'
    metadata: Dict[str, str] = None


class IACDetector:
    """
    Detects and analyzes Infrastructure as Code files
    """
    
    def __init__(self):
        self.iac_files: List[IACFile] = []
        
        # AWS service patterns for Terraform
        self.aws_terraform_patterns = {
            's3': [r'aws_s3_bucket', r'aws_s3_object', r'aws_s3_bucket_policy'],
            'lambda': [r'aws_lambda_function', r'aws_lambda_event_source_mapping'],
            'dynamodb': [r'aws_dynamodb_table', r'aws_dynamodb_table_item'],
            'sqs': [r'aws_sqs_queue', r'aws_sqs_queue_policy'],
            'sns': [r'aws_sns_topic', r'aws_sns_topic_subscription'],
            'rds': [r'aws_db_instance', r'aws_rds_cluster'],
            'ec2': [r'aws_instance', r'aws_launch_template'],
            'eks': [r'aws_eks_cluster', r'aws_eks_node_group'],
            'fargate': [r'aws_ecs_cluster', r'aws_ecs_service'],
            'cloudwatch': [r'aws_cloudwatch_log_group', r'aws_cloudwatch_metric_alarm'],
            'apigateway': [r'aws_api_gateway_rest_api', r'aws_api_gateway_resource'],
        }
        
        # Azure service patterns for Terraform
        self.azure_terraform_patterns = {
            'blob_storage': [r'azurerm_storage_account', r'azurerm_storage_container'],
            'functions': [r'azurerm_function_app', r'azurerm_function_app_function'],
            'cosmos_db': [r'azurerm_cosmosdb_account', r'azurerm_cosmosdb_sql_database'],
            'service_bus': [r'azurerm_servicebus_namespace', r'azurerm_servicebus_queue'],
            'aks': [r'azurerm_kubernetes_cluster'],
            'sql_database': [r'azurerm_sql_server', r'azurerm_sql_database'],
        }
        
        # CloudFormation resource types
        self.cloudformation_patterns = {
            's3': [r'AWS::S3::Bucket', r'AWS::S3::BucketPolicy'],
            'lambda': [r'AWS::Lambda::Function', r'AWS::Lambda::EventSourceMapping'],
            'dynamodb': [r'AWS::DynamoDB::Table'],
            'sqs': [r'AWS::SQS::Queue', r'AWS::SQS::QueuePolicy'],
            'sns': [r'AWS::SNS::Topic', r'AWS::SNS::Subscription'],
            'rds': [r'AWS::RDS::DBInstance', r'AWS::RDS::DBCluster'],
            'ec2': [r'AWS::EC2::Instance', r'AWS::EC2::LaunchTemplate'],
            'eks': [r'AWS::EKS::Cluster', r'AWS::EKS::Nodegroup'],
            'fargate': [r'AWS::ECS::Cluster', r'AWS::ECS::Service'],
        }
        
        # Service mappings to GCP
        self.service_mappings = {
            's3': 'cloud_storage',
            'lambda': 'cloud_functions',
            'dynamodb': 'firestore',
            'sqs': 'pubsub',
            'sns': 'pubsub',
            'rds': 'cloud_sql',
            'ec2': 'compute_engine',
            'eks': 'gke',
            'fargate': 'cloud_run',
            'cloudwatch': 'cloud_monitoring',
            'apigateway': 'apigee',
            'blob_storage': 'cloud_storage',
            'functions': 'cloud_functions',
            'cosmos_db': 'firestore',
            'service_bus': 'pubsub',
            'aks': 'gke',
            'sql_database': 'cloud_sql',
        }
    
    def detect_iac_files(self, repository_path: str) -> List[IACFile]:
        """
        Detect all Infrastructure as Code files in repository
        
        Args:
            repository_path: Path to repository root
            
        Returns:
            List of IACFile objects
        """
        self.iac_files = []
        
        # File patterns for different IaC types
        patterns = {
            IACType.TERRAFORM: ['.tf', '.tfvars'],
            IACType.CLOUDFORMATION: ['.yaml', '.yml', '.json'],
            IACType.PULUMI: ['.py'],  # Pulumi uses Python/TypeScript
            IACType.KUBERNETES: ['k8s.yaml', 'k8s.yml', 'kubernetes.yaml'],
            IACType.DOCKER_COMPOSE: ['docker-compose.yml', 'docker-compose.yaml'],
            IACType.ANSIBLE: ['playbook.yml', 'playbook.yaml'],
        }
        
        for root, dirs, files in os.walk(repository_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target']]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repository_path)
                
                # Detect IaC type
                iac_type = self._detect_iac_type(file_path, file)
                
                if iac_type != IACType.UNKNOWN:
                    # Analyze the file
                    iac_file = self._analyze_iac_file(file_path, relative_path, iac_type)
                    if iac_file:
                        self.iac_files.append(iac_file)
        
        return self.iac_files
    
    def _detect_iac_type(self, file_path: str, filename: str) -> IACType:
        """Detect the type of IaC file"""
        # Check by extension and content
        if filename.endswith(('.tf', '.tfvars')):
            return IACType.TERRAFORM
        
        if filename in ['docker-compose.yml', 'docker-compose.yaml']:
            return IACType.DOCKER_COMPOSE
        
        if 'k8s' in filename.lower() or 'kubernetes' in filename.lower():
            return IACType.KUBERNETES
        
        if filename.endswith(('.yaml', '.yml', '.json')):
            # Check content for CloudFormation
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'AWSTemplateFormatVersion' in content or 'Resources:' in content:
                        return IACType.CLOUDFORMATION
                    if 'apiVersion:' in content and 'kind:' in content:
                        return IACType.KUBERNETES
                    if 'hosts:' in content and 'tasks:' in content:
                        return IACType.ANSIBLE
            except Exception:
                pass
        
        if filename.endswith('.py'):
            # Check for Pulumi
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'import pulumi' in content or 'pulumi.' in content:
                        return IACType.PULUMI
            except Exception:
                pass
        
        return IACType.UNKNOWN
    
    def _analyze_iac_file(self, file_path: str, relative_path: str, iac_type: IACType) -> Optional[IACFile]:
        """Analyze an IaC file for cloud services"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            services_referenced = []
            gcp_services_mapped = {}
            
            # Detect services based on IaC type
            if iac_type == IACType.TERRAFORM:
                services_referenced, gcp_services_mapped = self._detect_terraform_services(content)
            elif iac_type == IACType.CLOUDFORMATION:
                services_referenced, gcp_services_mapped = self._detect_cloudformation_services(content)
            elif iac_type == IACType.PULUMI:
                services_referenced, gcp_services_mapped = self._detect_pulumi_services(content)
            elif iac_type == IACType.KUBERNETES:
                services_referenced, gcp_services_mapped = self._detect_kubernetes_services(content)
            
            # Estimate complexity
            complexity = self._estimate_complexity(content, len(services_referenced))
            
            # Estimate changes (rough: 5-20 lines per service)
            estimated_changes = len(services_referenced) * 10
            
            return IACFile(
                file_path=relative_path,
                iac_type=iac_type,
                services_referenced=services_referenced,
                gcp_services_mapped=gcp_services_mapped,
                estimated_changes=estimated_changes,
                complexity=complexity,
                metadata={'file_size': len(content)}
            )
            
        except Exception as e:
            # Skip files that can't be analyzed
            return None
    
    def _detect_terraform_services(self, content: str) -> tuple[List[str], Dict[str, str]]:
        """Detect AWS/Azure services in Terraform files"""
        services_found = set()
        gcp_mappings = {}
        
        # Check AWS patterns
        for service, patterns in self.aws_terraform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    services_found.add(service)
                    if service in self.service_mappings:
                        gcp_mappings[service] = self.service_mappings[service]
        
        # Check Azure patterns
        for service, patterns in self.azure_terraform_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    services_found.add(service)
                    if service in self.service_mappings:
                        gcp_mappings[service] = self.service_mappings[service]
        
        return list(services_found), gcp_mappings
    
    def _detect_cloudformation_services(self, content: str) -> tuple[List[str], Dict[str, str]]:
        """Detect AWS services in CloudFormation files"""
        services_found = set()
        gcp_mappings = {}
        
        try:
            # Parse YAML or JSON
            if content.strip().startswith('{'):
                data = json.loads(content)
            else:
                data = yaml.safe_load(content)
            
            # Check Resources section
            if isinstance(data, dict) and 'Resources' in data:
                resources = data['Resources']
                for resource_name, resource_def in resources.items():
                    if isinstance(resource_def, dict) and 'Type' in resource_def:
                        resource_type = resource_def['Type']
                        
                        # Check against CloudFormation patterns
                        for service, patterns in self.cloudformation_patterns.items():
                            for pattern in patterns:
                                if re.search(pattern, resource_type, re.IGNORECASE):
                                    services_found.add(service)
                                    if service in self.service_mappings:
                                        gcp_mappings[service] = self.service_mappings[service]
        except Exception:
            # Fallback to regex search
            for service, patterns in self.cloudformation_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        services_found.add(service)
                        if service in self.service_mappings:
                            gcp_mappings[service] = self.service_mappings[service]
        
        return list(services_found), gcp_mappings
    
    def _detect_pulumi_services(self, content: str) -> tuple[List[str], Dict[str, str]]:
        """Detect cloud services in Pulumi files"""
        services_found = set()
        gcp_mappings = {}
        
        # Pulumi uses patterns like aws.s3.Bucket, azure.storage.BlobContainer
        aws_patterns = {
            's3': r'aws\.s3\.|aws\.s3\.Bucket',
            'lambda': r'aws\.lambda\.|aws\.lambda\.Function',
            'dynamodb': r'aws\.dynamodb\.|aws\.dynamodb\.Table',
            'sqs': r'aws\.sqs\.|aws\.sqs\.Queue',
            'rds': r'aws\.rds\.|aws\.rds\.Instance',
            'eks': r'aws\.eks\.|aws\.eks\.Cluster',
        }
        
        azure_patterns = {
            'blob_storage': r'azure\.storage\.|azure\.storage\.BlobContainer',
            'functions': r'azure\.functions\.|azure\.functions\.FunctionApp',
            'cosmos_db': r'azure\.cosmosdb\.|azure\.cosmosdb\.Account',
            'service_bus': r'azure\.servicebus\.|azure\.servicebus\.Queue',
            'aks': r'azure\.containerservice\.|azure\.containerservice\.KubernetesCluster',
        }
        
        for service, pattern in aws_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                services_found.add(service)
                if service in self.service_mappings:
                    gcp_mappings[service] = self.service_mappings[service]
        
        for service, pattern in azure_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                services_found.add(service)
                if service in self.service_mappings:
                    gcp_mappings[service] = self.service_mappings[service]
        
        return list(services_found), gcp_mappings
    
    def _detect_kubernetes_services(self, content: str) -> tuple[List[str], Dict[str, str]]:
        """Detect cloud services in Kubernetes manifests"""
        services_found = set()
        gcp_mappings = {}
        
        # Kubernetes manifests might reference cloud services through annotations or config
        # Check for AWS/Azure specific annotations or service references
        aws_patterns = [
            r'arn:aws:', r'\.s3\.amazonaws\.com', r'\.dynamodb\.amazonaws\.com',
            r'eks\.amazonaws\.com', r'fargate'
        ]
        
        azure_patterns = [
            r'\.blob\.core\.windows\.net', r'\.cosmos\.azure\.com',
            r'aks\.microsoft\.com', r'azure\.com'
        ]
        
        for pattern in aws_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # Try to identify specific service
                if 's3' in pattern or 's3' in content.lower():
                    services_found.add('s3')
                    gcp_mappings['s3'] = 'cloud_storage'
                if 'dynamodb' in pattern or 'dynamodb' in content.lower():
                    services_found.add('dynamodb')
                    gcp_mappings['dynamodb'] = 'firestore'
                if 'eks' in pattern or 'eks' in content.lower():
                    services_found.add('eks')
                    gcp_mappings['eks'] = 'gke'
        
        for pattern in azure_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                if 'blob' in pattern or 'blob' in content.lower():
                    services_found.add('blob_storage')
                    gcp_mappings['blob_storage'] = 'cloud_storage'
                if 'cosmos' in pattern or 'cosmos' in content.lower():
                    services_found.add('cosmos_db')
                    gcp_mappings['cosmos_db'] = 'firestore'
                if 'aks' in pattern or 'aks' in content.lower():
                    services_found.add('aks')
                    gcp_mappings['aks'] = 'gke'
        
        return list(services_found), gcp_mappings
    
    def _estimate_complexity(self, content: str, service_count: int) -> str:
        """Estimate migration complexity"""
        lines = len(content.split('\n'))
        
        if service_count <= 2 and lines <= 100:
            return 'simple'
        elif service_count <= 5 and lines <= 500:
            return 'moderate'
        else:
            return 'complex'
