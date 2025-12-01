"""
Test for Azure to GCP functionality
"""

import unittest
from unittest.mock import Mock
from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedSemanticRefactoringService, AzureExtendedASTTransformationEngine
from infrastructure.adapters.service_mapping import ExtendedCodeAnalyzer
from infrastructure.adapters.azure_mapping import AzureServiceMapper
from domain.value_objects import AzureService, GCPService


class TestAzureFunctionality(unittest.TestCase):
    """Test cases for Azure to GCP migration"""
    
    def setUp(self):
        self.ast_engine = AzureExtendedASTTransformationEngine()
        self.service = AzureExtendedSemanticRefactoringService(self.ast_engine)
    
    def test_azure_service_mapper_exists(self):
        """Test that Azure service mapper exists and has mappings"""
        mapper = AzureServiceMapper()
        services = mapper.get_azure_services()
        
        self.assertGreater(len(services), 0)
        self.assertIn(AzureService.BLOB_STORAGE, services)
        self.assertIn(AzureService.FUNCTIONS, services)
    
    def test_azure_blob_storage_mapping_exists(self):
        """Test that Azure Blob Storage to GCS mapping exists"""
        mapper = AzureServiceMapper()
        mapping = mapper.get_mapping(AzureService.BLOB_STORAGE)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.CLOUD_STORAGE)
        self.assertEqual(mapping.azure_service, AzureService.BLOB_STORAGE)
    
    def test_azure_functions_mapping_exists(self):
        """Test that Azure Functions to Cloud Functions mapping exists"""
        mapper = AzureServiceMapper()
        mapping = mapper.get_mapping(AzureService.FUNCTIONS)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.CLOUD_FUNCTIONS)
        self.assertEqual(mapping.azure_service, AzureService.FUNCTIONS)
    
    def test_azure_blob_storage_to_gcs_transformation(self):
        """Test transforming Azure Blob Storage code to GCS code"""
        original_code = """
from azure.storage.blob import BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(conn_str="connection_string")
blob_client = blob_service_client.get_blob_client(container="container", blob="blob.txt")
data = blob_client.download_blob().content_as_text()
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "azure_blob_storage_to_gcs"
        )
        
        # The refactored code should contain GCS patterns
        self.assertIn("google.cloud", refactored_code)
        self.assertIn("storage.Client", refactored_code)
        self.assertNotIn("BlobServiceClient", refactored_code)
    
    def test_azure_functions_to_cloud_functions_transformation(self):
        """Test transforming Azure Functions code to Cloud Functions code"""
        original_code = """
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Hello, world!")
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "azure_functions_to_cloud_functions"
        )
        
        # The refactored code should contain Cloud Functions patterns
        self.assertIn("functions_framework", refactored_code)
        self.assertNotIn("azure.functions", refactored_code)
    
    def test_azure_analyzer_detects_services(self):
        """Test that the extended analyzer can detect Azure services"""
        code_with_azure = """
from azure.storage.blob import BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(conn_str="connection_string")
"""
        
        analyzer = ExtendedCodeAnalyzer()
        services_found = analyzer.identify_azure_services_usage(code_with_azure)
        
        self.assertIn(AzureService.BLOB_STORAGE, services_found)
    
    def test_azure_identify_all_cloud_services(self):
        """Test that the analyzer identifies both AWS and Azure services"""
        code_with_both = """
# AWS service
import boto3
s3_client = boto3.client('s3')

# Azure service
from azure.storage.blob import BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(conn_str="connection_string")
"""
        
        analyzer = ExtendedCodeAnalyzer()
        all_services = analyzer.identify_all_cloud_services_usage(code_with_both)
        
        # Should find both AWS and Azure services
        aws_found = any('aws_' in service for service in all_services.keys())
        azure_found = any('azure_' in service for service in all_services.keys())
        
        self.assertTrue(aws_found, "AWS services should be detected")
        self.assertTrue(azure_found, "Azure services should be detected")
    
    def test_azure_key_vault_mapping_exists(self):
        """Test that Azure Key Vault to Secret Manager mapping exists"""
        mapper = AzureServiceMapper()
        mapping = mapper.get_mapping(AzureService.KEY_VAULT)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.SECRET_MANAGER)
        self.assertEqual(mapping.azure_service, AzureService.KEY_VAULT)
        self.assertIn("SecretClient", mapping.azure_api_patterns[0])
        self.assertIn("secretmanager", mapping.gcp_sdk_imports[0])
    
    def test_azure_application_insights_mapping_exists(self):
        """Test that Azure Application Insights to Cloud Monitoring mapping exists"""
        mapper = AzureServiceMapper()
        mapping = mapper.get_mapping(AzureService.APPLICATION_INSIGHTS)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.CLOUD_MONITORING)
        self.assertEqual(mapping.azure_service, AzureService.APPLICATION_INSIGHTS)
        self.assertIn("TelemetryClient", mapping.azure_api_patterns[1])
        self.assertIn("monitoring_v3", mapping.gcp_sdk_imports[0])
    
    def test_azure_key_vault_to_secret_manager_transformation(self):
        """Test transforming Azure Key Vault code to Secret Manager code"""
        original_code = """
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

vault_url = "https://myvault.vault.azure.net/"
credential = DefaultAzureCredential()
client = SecretClient(vault_url=vault_url, credential=credential)

secret = client.get_secret("my-secret")
print(f"Secret value: {secret.value}")
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "azure_key_vault_to_secret_manager"
        )
        
        # The refactored code should contain Secret Manager patterns
        self.assertIn("google.cloud.secretmanager", refactored_code)
        self.assertIn("SecretManagerServiceClient", refactored_code)
        self.assertNotIn("SecretClient", refactored_code)
        self.assertNotIn("azure.keyvault", refactored_code)
    
    def test_azure_application_insights_to_monitoring_transformation(self):
        """Test transforming Azure Application Insights code to Cloud Monitoring code"""
        original_code = """
from applicationinsights import TelemetryClient

telemetry_client = TelemetryClient(instrumentation_key="key")
telemetry_client.track_event("UserAction", {"user_id": "123"})
telemetry_client.track_metric("ResponseTime", 150.5)
telemetry_client.track_trace("Processing started")
telemetry_client.flush()
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "azure_application_insights_to_monitoring"
        )
        
        # The refactored code should contain Cloud Monitoring/Logging patterns
        self.assertIn("google.cloud", refactored_code)
        self.assertIn("monitoring_v3", refactored_code.lower() or "logging" in refactored_code.lower())
        self.assertNotIn("TelemetryClient", refactored_code)
        self.assertNotIn("applicationinsights", refactored_code)
    
    def test_all_15_azure_services_mapped(self):
        """Test that all 15 Azure services have mappings"""
        mapper = AzureServiceMapper()
        services = mapper.get_azure_services()
        
        expected_services = [
            AzureService.BLOB_STORAGE,
            AzureService.FUNCTIONS,
            AzureService.COSMOS_DB,
            AzureService.SERVICE_BUS,
            AzureService.EVENT_HUBS,
            AzureService.SQL_DATABASE,
            AzureService.VIRTUAL_MACHINES,
            AzureService.MONITOR,
            AzureService.API_MANAGEMENT,
            AzureService.REDIS_CACHE,
            AzureService.AKS,
            AzureService.CONTAINER_INSTANCES,
            AzureService.APP_SERVICE,
            AzureService.KEY_VAULT,
            AzureService.APPLICATION_INSIGHTS
        ]
        
        self.assertEqual(len(services), 15, f"Expected 15 services, got {len(services)}")
        for service in expected_services:
            self.assertIn(service, services, f"{service} should be in the list")
            mapping = mapper.get_mapping(service)
            self.assertIsNotNone(mapping, f"Mapping for {service} should exist")


if __name__ == '__main__':
    unittest.main()