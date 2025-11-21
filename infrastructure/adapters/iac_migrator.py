"""
Infrastructure as Code (IaC) Migrator

Architectural Intent:
- Migrates Infrastructure as Code files from AWS/Azure to GCP
- Supports Terraform, CloudFormation, and Pulumi
- Preserves infrastructure intent while updating to GCP resources
"""

import os
import re
import json
import yaml
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from infrastructure.adapters.iac_detector import IACDetector, IACFile, IACType


class IACMigrator:
    """
    Migrates Infrastructure as Code files to GCP equivalents
    """
    
    def __init__(self):
        self.detector = IACDetector()
        
        # Terraform resource mappings: AWS/Azure -> GCP
        self.terraform_mappings = {
            # Storage
            'aws_s3_bucket': 'google_storage_bucket',
            'aws_s3_object': 'google_storage_bucket_object',
            'azurerm_storage_account': 'google_storage_bucket',
            'azurerm_storage_container': 'google_storage_bucket',
            
            # Compute
            'aws_lambda_function': 'google_cloudfunctions_function',
            'aws_instance': 'google_compute_instance',
            'azurerm_function_app': 'google_cloudfunctions_function',
            'azurerm_virtual_machine': 'google_compute_instance',
            
            # Database
            'aws_dynamodb_table': 'google_firestore_database',
            'aws_db_instance': 'google_sql_database_instance',
            'azurerm_cosmosdb_account': 'google_firestore_database',
            'azurerm_sql_database': 'google_sql_database_instance',
            
            # Messaging
            'aws_sqs_queue': 'google_pubsub_topic',
            'aws_sns_topic': 'google_pubsub_topic',
            'azurerm_servicebus_queue': 'google_pubsub_topic',
            
            # Containers
            'aws_eks_cluster': 'google_container_cluster',
            'azurerm_kubernetes_cluster': 'google_container_cluster',
            'aws_ecs_cluster': 'google_cloud_run_service',
            'aws_ecs_service': 'google_cloud_run_service',
            
            # Monitoring
            'aws_cloudwatch_log_group': 'google_logging_log_sink',
            'azurerm_monitor_action_group': 'google_monitoring_notification_channel',
            
            # API Gateway
            'aws_api_gateway_rest_api': 'google_api_gateway_api',
            'azurerm_api_management': 'google_api_gateway_api',
        }
        
        # CloudFormation to Terraform mappings (we'll convert CF to TF)
        self.cloudformation_to_gcp = {
            'AWS::S3::Bucket': 'google_storage_bucket',
            'AWS::Lambda::Function': 'google_cloudfunctions_function',
            'AWS::DynamoDB::Table': 'google_firestore_database',
            'AWS::SQS::Queue': 'google_pubsub_topic',
            'AWS::SNS::Topic': 'google_pubsub_topic',
            'AWS::RDS::DBInstance': 'google_sql_database_instance',
            'AWS::EC2::Instance': 'google_compute_instance',
            'AWS::EKS::Cluster': 'google_container_cluster',
            'AWS::ECS::Cluster': 'google_cloud_run_service',
        }
    
    def migrate_iac_file(self, file_path: str, iac_file: IACFile) -> Tuple[str, bool]:
        """
        Migrate an IaC file to GCP
        
        Args:
            file_path: Full path to the IaC file
            iac_file: IACFile object with detected services
            
        Returns:
            Tuple of (migrated_content, success)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            if iac_file.iac_type == IACType.TERRAFORM:
                migrated_content = self._migrate_terraform(original_content, iac_file)
            elif iac_file.iac_type == IACType.CLOUDFORMATION:
                migrated_content = self._migrate_cloudformation(original_content, iac_file)
            elif iac_file.iac_type == IACType.PULUMI:
                migrated_content = self._migrate_pulumi(original_content, iac_file)
            else:
                # For other types, return original with comment
                migrated_content = f"# TODO: Migrate {iac_file.iac_type.value} to GCP equivalent\n{original_content}"
            
            return migrated_content, True
            
        except Exception as e:
            # Return original with error comment
            error_content = f"# ERROR: Failed to migrate IaC file: {str(e)}\n{original_content}"
            return error_content, False
    
    def _migrate_terraform(self, content: str, iac_file: IACFile) -> str:
        """Migrate Terraform file to GCP"""
        migrated = content
        
        # Replace provider declarations
        migrated = re.sub(
            r'provider\s+"aws"\s*\{[^}]*\}',
            'provider "google" {\n  project = var.gcp_project_id\n  region  = var.gcp_region\n}',
            migrated,
            flags=re.MULTILINE | re.DOTALL
        )
        
        migrated = re.sub(
            r'provider\s+"azurerm"\s*\{[^}]*\}',
            'provider "google" {\n  project = var.gcp_project_id\n  region  = var.gcp_region\n}',
            migrated,
            flags=re.MULTILINE | re.DOTALL
        )
        
        # Replace resource types
        for aws_resource, gcp_resource in self.terraform_mappings.items():
            # Match resource blocks
            pattern = rf'resource\s+"{re.escape(aws_resource)}"'
            replacement = f'resource "{gcp_resource}"'
            migrated = re.sub(pattern, replacement, migrated, flags=re.IGNORECASE)
        
        # Update data sources
        migrated = re.sub(
            r'data\s+"aws_([^"]+)"',
            r'data "google_\1"',
            migrated,
            flags=re.IGNORECASE
        )
        
        # Add GCP provider requirement
        if 'terraform {' not in migrated:
            migrated = 'terraform {\n  required_providers {\n    google = {\n      source  = "hashicorp/google"\n      version = "~> 5.0"\n    }\n  }\n}\n\n' + migrated
        elif 'required_providers' not in migrated:
            migrated = re.sub(
                r'(terraform\s*\{)',
                r'\1\n  required_providers {\n    google = {\n      source  = "hashicorp/google"\n      version = "~> 5.0"\n    }\n  }',
                migrated,
                flags=re.IGNORECASE
            )
        
        # Add variable declarations for GCP if not present
        if 'var.gcp_project_id' in migrated and 'variable "gcp_project_id"' not in migrated:
            variables = '''
variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}
'''
            migrated = variables + migrated
        
        # Add migration comment at top
        if not migrated.startswith('#'):
            migrated = f"# Migrated from {', '.join(iac_file.services_referenced)} to GCP\n# Generated by Universal Cloud Refactor Agent\n\n{migrated}"
        
        return migrated
    
    def _migrate_cloudformation(self, content: str, iac_file: IACFile) -> str:
        """Migrate CloudFormation to Terraform (GCP)"""
        try:
            # Parse CloudFormation
            if content.strip().startswith('{'):
                cf_data = json.loads(content)
            else:
                cf_data = yaml.safe_load(content)
            
            # Convert to Terraform
            terraform_content = self._convert_cf_to_terraform(cf_data, iac_file)
            
            return terraform_content
            
        except Exception as e:
            # Fallback: return original with conversion instructions
            return f"""# CloudFormation to Terraform (GCP) Conversion
# Original CloudFormation file preserved below
# Manual conversion required for complex resources
# Error during conversion: {str(e)}

{content}
"""
    
    def _convert_cf_to_terraform(self, cf_data: Dict, iac_file: IACFile) -> str:
        """Convert CloudFormation to Terraform"""
        terraform_parts = [
            '# Migrated from CloudFormation to Terraform (GCP)',
            '# Generated by Universal Cloud Refactor Agent',
            '',
            'terraform {',
            '  required_providers {',
            '    google = {',
            '      source  = "hashicorp/google"',
            '      version = "~> 5.0"',
            '    }',
            '  }',
            '}',
            '',
            'provider "google" {',
            '  project = var.gcp_project_id',
            '  region  = var.gcp_region',
            '}',
            '',
            'variable "gcp_project_id" {',
            '  description = "GCP Project ID"',
            '  type        = string',
            '}',
            '',
            'variable "gcp_region" {',
            '  description = "GCP Region"',
            '  type        = string',
            '  default     = "us-central1"',
            '}',
            '',
        ]
        
        # Convert Resources
        if 'Resources' in cf_data:
            terraform_parts.append('# Resources migrated from CloudFormation')
            terraform_parts.append('')
            
            for resource_name, resource_def in cf_data['Resources'].items():
                if isinstance(resource_def, dict) and 'Type' in resource_def:
                    cf_type = resource_def['Type']
                    properties = resource_def.get('Properties', {})
                    
                    # Map to GCP Terraform resource
                    gcp_resource = self.cloudformation_to_gcp.get(cf_type)
                    if gcp_resource:
                        terraform_parts.append(f'resource "{gcp_resource}" "{resource_name.lower()}" {{')
                        terraform_parts.append(f'  # Migrated from {cf_type}')
                        
                        # Add basic properties (simplified)
                        if 'Name' in properties:
                            terraform_parts.append(f'  name = "{properties["Name"]}"')
                        
                        terraform_parts.append('}')
                        terraform_parts.append('')
        
        # Convert Outputs
        if 'Outputs' in cf_data:
            terraform_parts.append('# Outputs')
            terraform_parts.append('')
            for output_name, output_def in cf_data['Outputs'].items():
                if isinstance(output_def, dict) and 'Value' in output_def:
                    terraform_parts.append(f'output "{output_name.lower()}" {{')
                    terraform_parts.append(f'  value = # TODO: Map CloudFormation output')
                    terraform_parts.append('}')
                    terraform_parts.append('')
        
        return '\n'.join(terraform_parts)
    
    def _migrate_pulumi(self, content: str, iac_file: IACFile) -> str:
        """Migrate Pulumi file to GCP"""
        migrated = content
        
        # Replace imports
        migrated = re.sub(
            r'import pulumi_aws',
            'import pulumi_gcp',
            migrated
        )
        
        migrated = re.sub(
            r'import pulumi_azure',
            'import pulumi_gcp',
            migrated
        )
        
        # Replace resource instantiations
        # aws.s3.Bucket -> gcp.storage.Bucket
        migrated = re.sub(
            r'aws\.s3\.Bucket',
            'gcp.storage.Bucket',
            migrated
        )
        
        migrated = re.sub(
            r'aws\.lambda\.Function',
            'gcp.cloudfunctions.Function',
            migrated
        )
        
        migrated = re.sub(
            r'aws\.dynamodb\.Table',
            'gcp.firestore.Database',
            migrated
        )
        
        migrated = re.sub(
            r'azure\.storage\.BlobContainer',
            'gcp.storage.Bucket',
            migrated
        )
        
        migrated = re.sub(
            r'azure\.functions\.FunctionApp',
            'gcp.cloudfunctions.Function',
            migrated
        )
        
        # Add migration comment
        if not migrated.startswith('#'):
            migrated = f"# Migrated from AWS/Azure to GCP\n# Generated by Universal Cloud Refactor Agent\n\n{migrated}"
        
        return migrated
    
    def migrate_all_iac_files(self, repository_path: str) -> Dict[str, Tuple[str, bool]]:
        """
        Migrate all IaC files in repository
        
        Args:
            repository_path: Path to repository root
            
        Returns:
            Dict mapping file paths to (migrated_content, success) tuples
        """
        results = {}
        
        # Detect all IaC files
        iac_files = self.detector.detect_iac_files(repository_path)
        
        for iac_file in iac_files:
            full_path = os.path.join(repository_path, iac_file.file_path)
            migrated_content, success = self.migrate_iac_file(full_path, iac_file)
            results[iac_file.file_path] = (migrated_content, success)
        
        return results
