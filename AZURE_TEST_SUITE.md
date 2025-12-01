# Azure to GCP Migration Test Suite

## Overview

Comprehensive test suite for Azure to GCP migration covering all **15 Azure services** with extensive test cases.

## Test Files

### 1. `test_azure_comprehensive.py`
**API Integration Tests** - Tests all Azure services via the API endpoint

- **22 Python test cases** covering all 15 Azure services
- **2 C# test cases** for Blob Storage and Key Vault
- Tests real-world code patterns
- Validates transformations via API
- Checks for expected GCP patterns and forbidden Azure patterns

**Services Tested:**
1. Blob Storage (basic + SAS URLs)
2. Functions (HTTP trigger + Blob trigger)
3. Cosmos DB
4. Service Bus (Queue + Topic)
5. Event Hubs (Producer + Consumer)
6. SQL Database
7. Virtual Machines
8. Monitor
9. API Management
10. Redis Cache
11. AKS
12. Container Instances
13. App Service
14. Key Vault 🆕
15. Application Insights 🆕

**Multi-Service Tests:**
- Blob Storage + Cosmos DB
- Functions + Key Vault

### 2. `tests/infrastructure/test_azure_functionality.py`
**Unit Tests** - Tests Azure service mappings and transformations

- Tests service mapper existence
- Tests mapping correctness
- Tests transformation methods
- Validates all 15 services are mapped

**New Tests Added:**
- `test_azure_key_vault_mapping_exists()`
- `test_azure_application_insights_mapping_exists()`
- `test_azure_key_vault_to_secret_manager_transformation()`
- `test_azure_application_insights_to_monitoring_transformation()`
- `test_all_15_azure_services_mapped()`

### 3. `tests/infrastructure/test_azure_key_vault_application_insights.py`
**Focused Unit Tests** - Detailed tests for new services

**Key Vault Tests:**
- Import replacement
- Client instantiation replacement
- `get_secret()` → `access_secret_version()`
- `set_secret()` → `create_secret()` + `add_secret_version()`
- Environment variable replacement

**Application Insights Tests:**
- Import replacement
- `TelemetryClient` → `Logging Client`
- `track_event()` → `log_struct()`
- `track_exception()` → `log_struct()` with ERROR severity
- `track_metric()` → `create_time_series()`
- `track_trace()` → `log_text()`
- `flush()` → comment (GCP logging is async)
- Environment variable replacement

**Multi-Service Integration Tests:**
- Functions + Key Vault
- Blob Storage + Application Insights

## Running Tests

### Run Comprehensive API Tests
```bash
# Start API server first
python api_server.py

# In another terminal, run comprehensive tests
python test_azure_comprehensive.py
```

### Run Unit Tests
```bash
# Run all Azure unit tests
python -m pytest tests/infrastructure/test_azure_functionality.py -v

# Run Key Vault and Application Insights tests
python -m pytest tests/infrastructure/test_azure_key_vault_application_insights.py -v

# Run all Azure tests
python -m pytest tests/infrastructure/test_azure*.py -v
```

## Test Coverage

### Service Coverage: 15/15 (100%)
✅ All 15 Azure services have test cases

### Pattern Coverage
- **Imports**: Azure SDK → GCP SDK
- **Client Instantiation**: Azure clients → GCP clients
- **API Methods**: Azure methods → GCP equivalents
- **Environment Variables**: Azure env vars → GCP env vars
- **Error Handling**: Azure exceptions → GCP exceptions
- **Multi-Service**: Multiple Azure services in one codebase

### Language Coverage
- ✅ Python (comprehensive)
- ✅ C# (basic)
- ⚠️ Java (can be added)

## Expected Test Results

### Success Criteria
1. ✅ All Azure patterns removed from refactored code
2. ✅ All GCP patterns present in refactored code
3. ✅ Code is syntactically valid
4. ✅ No Azure SDK imports remain
5. ✅ Environment variables correctly translated

### Validation Checks
- **Expected Patterns**: Must be present in refactored code
- **Forbidden Patterns**: Must NOT be present in refactored code
- **Syntax Validation**: Code must be valid Python/C#/Java
- **API Correctness**: GCP APIs must be used correctly

## Test Output

Tests generate:
- Console output with test progress
- `test_azure_results.json` with detailed results
- Service breakdown showing pass/fail per service

## Example Test Case

```python
"key_vault_secrets": {
    "code": """from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

vault_url = "https://myvault.vault.azure.net/"
credential = DefaultAzureCredential()
client = SecretClient(vault_url=vault_url, credential=credential)

client.set_secret("my-secret", "my-secret-value")
secret = client.get_secret("my-secret")
print(f"Secret value: {secret.value}")
""",
    "services": ["key_vault"],
    "expected": [
        "google.cloud.secretmanager",
        "SecretManagerServiceClient",
        "access_secret_version",
        "create_secret"
    ],
    "forbidden": [
        "azure.keyvault.secrets",
        "SecretClient",
        "AZURE_KEY_VAULT_URL"
    ]
}
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:
- Run on every commit
- Validate Azure migrations before deployment
- Ensure no regressions in Azure support

## Future Enhancements

- [ ] Add Java test cases
- [ ] Add more C# test cases
- [ ] Add performance benchmarks
- [ ] Add edge case tests
- [ ] Add integration tests with actual GCP services
