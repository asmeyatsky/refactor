"""
Unit tests for Azure Key Vault and Application Insights migrations

Architectural Intent:
- Test the new Azure services (Key Vault and Application Insights) transformations
- Verify correct mapping to GCP equivalents (Secret Manager and Cloud Monitoring)
- Ensure all patterns are correctly transformed
"""

import unittest
from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedPythonTransformer
from infrastructure.adapters.azure_mapping import AzureServiceMapper
from domain.value_objects import AzureService, GCPService


class TestAzureKeyVaultMigration(unittest.TestCase):
    """Test cases for Azure Key Vault to Secret Manager migration"""
    
    def setUp(self):
        self.transformer = AzureExtendedPythonTransformer(None, AzureServiceMapper())
        self.mapper = AzureServiceMapper()
    
    def test_key_vault_mapping_exists(self):
        """Test that Key Vault mapping exists"""
        mapping = self.mapper.get_mapping(AzureService.KEY_VAULT)
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.SECRET_MANAGER)
    
    def test_key_vault_imports_replaced(self):
        """Test that Azure Key Vault imports are replaced"""
        code = """from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential"""
        
        transformed = self.transformer._migrate_azure_key_vault_to_secret_manager(code)
        
        self.assertIn("google.cloud.secretmanager", transformed)
        self.assertNotIn("azure.keyvault.secrets", transformed)
        self.assertNotIn("azure.identity", transformed)
    
    def test_secret_client_instantiation_replaced(self):
        """Test that SecretClient instantiation is replaced"""
        code = """vault_url = "https://myvault.vault.azure.net/"
credential = DefaultAzureCredential()
client = SecretClient(vault_url=vault_url, credential=credential)"""
        
        transformed = self.transformer._migrate_azure_key_vault_to_secret_manager(code)
        
        self.assertIn("SecretManagerServiceClient", transformed)
        self.assertNotIn("SecretClient", transformed)
    
    def test_get_secret_replaced(self):
        """Test that get_secret() is replaced with access_secret_version()"""
        code = """client = SecretClient(vault_url="https://vault.vault.azure.net/", credential=cred)
secret = client.get_secret("my-secret")"""
        
        transformed = self.transformer._migrate_azure_key_vault_to_secret_manager(code)
        
        self.assertIn("access_secret_version", transformed)
        self.assertNotIn("get_secret", transformed)
    
    def test_set_secret_replaced(self):
        """Test that set_secret() is replaced with create_secret()"""
        code = """client = SecretClient(vault_url="https://vault.vault.azure.net/", credential=cred)
client.set_secret(name="my-secret", value="my-value")"""
        
        transformed = self.transformer._migrate_azure_key_vault_to_secret_manager(code)
        
        self.assertIn("create_secret", transformed)
        self.assertIn("add_secret_version", transformed)
    
    def test_environment_variables_replaced(self):
        """Test that Azure environment variables are replaced"""
        code = """vault_url = os.getenv('AZURE_KEY_VAULT_URL')
client_id = os.getenv('AZURE_CLIENT_ID')
client_secret = os.getenv('AZURE_CLIENT_SECRET')"""
        
        transformed = self.transformer._migrate_azure_key_vault_to_secret_manager(code)
        
        self.assertIn("GOOGLE_CLOUD_PROJECT", transformed)
        self.assertIn("GOOGLE_APPLICATION_CREDENTIALS", transformed)
        self.assertNotIn("AZURE_KEY_VAULT_URL", transformed)


class TestAzureApplicationInsightsMigration(unittest.TestCase):
    """Test cases for Azure Application Insights to Cloud Monitoring migration"""
    
    def setUp(self):
        self.transformer = AzureExtendedPythonTransformer(None, AzureServiceMapper())
        self.mapper = AzureServiceMapper()
    
    def test_application_insights_mapping_exists(self):
        """Test that Application Insights mapping exists"""
        mapping = self.mapper.get_mapping(AzureService.APPLICATION_INSIGHTS)
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.CLOUD_MONITORING)
    
    def test_application_insights_imports_replaced(self):
        """Test that Application Insights imports are replaced"""
        code = """from azure.applicationinsights import ApplicationInsightsClient
import applicationinsights"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("google.cloud.monitoring_v3", transformed)
        self.assertIn("google.cloud.logging", transformed)
        self.assertNotIn("azure.applicationinsights", transformed)
        self.assertNotIn("import applicationinsights", transformed)
    
    def test_telemetry_client_replaced(self):
        """Test that TelemetryClient is replaced with Logging Client"""
        code = """telemetry_client = TelemetryClient(instrumentation_key="key")"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("logging.Client", transformed)
        self.assertNotIn("TelemetryClient", transformed)
    
    def test_track_event_replaced(self):
        """Test that track_event() is replaced with log_struct()"""
        code = """telemetry_client.track_event(name="UserAction", properties={"user_id": "123"})"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("log_struct", transformed)
        self.assertNotIn("track_event", transformed)
    
    def test_track_exception_replaced(self):
        """Test that track_exception() is replaced with log_struct()"""
        code = """try:
    raise ValueError("Error")
except Exception as e:
    telemetry_client.track_exception(exception=e, properties={"severity": "high"})"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("log_struct", transformed)
        self.assertIn("ERROR", transformed)
        self.assertNotIn("track_exception", transformed)
    
    def test_track_metric_replaced(self):
        """Test that track_metric() is replaced with create_time_series()"""
        code = """telemetry_client.track_metric(name="ResponseTime", value=150.5)"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("create_time_series", transformed)
        self.assertIn("monitoring_v3", transformed)
        self.assertNotIn("track_metric", transformed)
    
    def test_track_trace_replaced(self):
        """Test that track_trace() is replaced with log_text()"""
        code = """telemetry_client.track_trace(message="Processing started")"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("log_text", transformed)
        self.assertNotIn("track_trace", transformed)
    
    def test_flush_replaced(self):
        """Test that flush() is replaced with comment"""
        code = """telemetry_client.flush()"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("# Flush not needed", transformed)
        self.assertNotIn("flush()", transformed)
    
    def test_environment_variables_replaced(self):
        """Test that Application Insights environment variables are replaced"""
        code = """key = os.getenv('APPINSIGHTS_INSTRUMENTATION_KEY')
conn_str = os.getenv('APPINSIGHTS_CONNECTION_STRING')"""
        
        transformed = self.transformer._migrate_azure_application_insights_to_monitoring(code)
        
        self.assertIn("GOOGLE_CLOUD_PROJECT", transformed)
        self.assertNotIn("APPINSIGHTS_INSTRUMENTATION_KEY", transformed)
        self.assertNotIn("APPINSIGHTS_CONNECTION_STRING", transformed)


class TestAzureMultiServiceMigration(unittest.TestCase):
    """Test cases for multi-service Azure migrations"""
    
    def setUp(self):
        self.transformer = AzureExtendedPythonTransformer(None, AzureServiceMapper())
    
    def test_functions_with_key_vault(self):
        """Test Azure Functions with Key Vault integration"""
        code = """import azure.functions as func
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def main(req: func.HttpRequest) -> func.HttpResponse:
    vault_url = "https://myvault.vault.azure.net/"
    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    secret = client.get_secret("api-key")
    return func.HttpResponse(f"Key: {secret.value[:5]}...")"""
        
        transformed = self.transformer._auto_detect_and_migrate(code)
        
        # Should transform both Functions and Key Vault
        self.assertIn("functions_framework", transformed)
        self.assertIn("secretmanager", transformed)
        self.assertNotIn("azure.functions", transformed)
        self.assertNotIn("azure.keyvault", transformed)
    
    def test_blob_storage_with_application_insights(self):
        """Test Azure Blob Storage with Application Insights"""
        code = """from azure.storage.blob import BlobServiceClient
from applicationinsights import TelemetryClient

blob_client = BlobServiceClient.from_connection_string("conn_str")
telemetry = TelemetryClient("instrumentation_key")

telemetry.track_event("BlobUploaded", {"blob_name": "file.txt"})
blob_client.get_blob_client("container", "blob.txt").upload_blob("data")"""
        
        transformed = self.transformer._auto_detect_and_migrate(code)
        
        # Should transform both Blob Storage and Application Insights
        self.assertIn("google.cloud.storage", transformed)
        self.assertIn("google.cloud.logging", transformed or "monitoring_v3" in transformed)
        self.assertNotIn("azure.storage.blob", transformed)
        self.assertNotIn("applicationinsights", transformed)


if __name__ == '__main__':
    unittest.main()
