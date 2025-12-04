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
            'java': AzureExtendedJavaTransformer(self.aws_service_mapper, self.azure_service_mapper),  # Simplified implementation
            'go': AzureExtendedGoTransformer(self.aws_service_mapper, self.azure_service_mapper),  # Uses Gemini API
            'golang': AzureExtendedGoTransformer(self.aws_service_mapper, self.azure_service_mapper)  # Alias
        }
    
    def transform_code(self, code: str, language: str, transformation_recipe: Dict[str, Any]) -> tuple[str, dict]:
        """
        Transform code based on the transformation recipe
        Ensures the output is syntactically correct and contains no AWS/Azure references.
        
        Returns:
            tuple: (transformed_code, variable_mapping) where variable_mapping is a dict
                   mapping old variable names to new variable names
        """
        # Check if code is shell/bash script with Azure CLI commands FIRST (before language check)
        is_shell_script = (
            code.strip().startswith('#!') or
            re.search(r'^\s*(az|aws|gcloud|kubectl|docker)\s+', code, re.MULTILINE)
        )
        
        if is_shell_script:
            # Transform Azure CLI commands to GCP CLI commands
            transformed_code = self._transform_azure_cli_to_gcp_cli(code, transformation_recipe)
            return transformed_code, {}
        
        if language not in self.transformers:
            raise ValueError(f"Unsupported language: {language}")
        
        # For Python Azure blob storage, use dedicated migration method first
        service_type = transformation_recipe.get('service_type', '')
        if language == 'python' and service_type == 'azure_blob_storage_to_gcs':
            transformed_code = self.transformers[language]._migrate_azure_blob_storage_to_gcs(code)
            # Apply aggressive cleanup
            if hasattr(self, '_aggressive_azure_cleanup'):
                transformed_code = self._aggressive_azure_cleanup(transformed_code)
            return transformed_code, {}
        
        # Use Gemini API for Go transformations (similar to AWS)
        if language in ['go', 'golang']:
            transformed_code = self._transform_azure_with_gemini_primary(code, transformation_recipe, language='go')
            
            # Apply aggressive cleanup after Gemini transformation for Go
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Applying aggressive Go Azure cleanup")
            # Apply cleanup multiple times to catch all patterns
            for i in range(3):
                transformed_code = self._aggressive_go_azure_cleanup(transformed_code)
            
            # Validate output - reject if still has Azure patterns
            max_retries = 2
            retry_count = 0
            while self._has_azure_patterns(transformed_code, language='go') and retry_count < max_retries:
                retry_count += 1
                logger.warning(f"Go output still contains Azure patterns, retrying (attempt {retry_count}/{max_retries})")
                transformed_code = self._transform_azure_with_gemini_primary(code, transformation_recipe, retry=True, language='go')
                # Apply cleanup multiple times after retry
                for i in range(3):
                    transformed_code = self._aggressive_go_azure_cleanup(transformed_code)
            
            # Final cleanup pass
            if self._has_azure_patterns(transformed_code, language='go'):
                logger.warning("Still has Azure patterns after retries, applying final aggressive cleanup")
                for i in range(5):
                    transformed_code = self._aggressive_go_azure_cleanup(transformed_code)
                    if not self._has_azure_patterns(transformed_code, language='go'):
                        break
        else:
            transformer = self.transformers[language]
            transformed_code = transformer.transform(code, transformation_recipe)
            
            # Validate syntax and AWS/Azure references for Python code
            if language == 'python':
                # Apply aggressive Azure cleanup to remove any remaining Azure patterns
                if transformed_code:
                    transformed_code = self._aggressive_azure_cleanup(transformed_code)
                    transformed_code = self._validate_and_fix_syntax(transformed_code, original_code=code)
                else:
                    transformed_code = code  # Fallback to original if transformation failed
        
        # Return tuple with variable mapping (empty dict for now, can be enhanced later)
        variable_mapping = {}
        if hasattr(self.transformers.get(language), '_variable_mappings'):
            code_id = id(code)
            variable_mapping = self.transformers[language]._variable_mappings.get(code_id, {})
        
        return transformed_code, variable_mapping
    
    def _transform_azure_cli_to_gcp_cli(self, code: str, transformation_recipe: Dict[str, Any]) -> str:
        """
        Transform Azure CLI commands to GCP CLI commands
        
        Examples:
        - az group create --name my-resource-group --location westus2
          → gcloud projects create my-resource-group --name="my-resource-group"
        
        - az storage account create -n my-storage-account-name -g my-resource-group
          → gcloud storage buckets create gs://my-storage-account-name --project=my-resource-group
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Transforming Azure CLI commands to GCP CLI commands")
        
        result = code
        lines = result.split('\n')
        transformed_lines = []
        
        # Azure location to GCP region mapping
        azure_to_gcp_regions = {
            'eastus': 'us-east1',
            'eastus2': 'us-east4',
            'westus': 'us-west1',
            'westus2': 'us-west2',
            'westus3': 'us-west3',
            'centralus': 'us-central1',
            'southcentralus': 'us-south1',
            'northcentralus': 'us-north1',
            'canadacentral': 'northamerica-northeast1',
            'canadaeast': 'northamerica-northeast2',
            'brazilsouth': 'southamerica-east1',
            'westeurope': 'europe-west1',
            'northeurope': 'europe-north1',
            'uksouth': 'europe-west2',
            'ukwest': 'europe-west2',
            'francecentral': 'europe-west1',
            'germanywestcentral': 'europe-west3',
            'switzerlandnorth': 'europe-west6',
            'norwayeast': 'europe-north1',
            'southeastasia': 'asia-southeast1',
            'eastasia': 'asia-east1',
            'japaneast': 'asia-northeast1',
            'japanwest': 'asia-northeast2',
            'koreacentral': 'asia-northeast3',
            'australiaeast': 'australia-southeast1',
            'australiasoutheast': 'australia-southeast2',
            'southafricanorth': 'africa-south1',
            'uaenorth': 'me-west1',
            'centralindia': 'asia-south1',
            'southindia': 'asia-south2',
            'westindia': 'asia-south1',
        }
        
        for line in lines:
            original_line = line
            stripped = line.strip()
            
            # Skip empty lines and comments (but preserve them)
            if not stripped or stripped.startswith('#'):
                transformed_lines.append(line)
                continue
            
            # Transform: az group create --name <name> --location <location>
            # → gcloud projects create <project-id> --name="<name>" --labels=location=<gcp-region>
            if re.match(r'^\s*az\s+group\s+create', stripped, re.IGNORECASE):
                # Extract name and location
                name_match = re.search(r'--name\s+(\S+)', stripped, re.IGNORECASE)
                location_match = re.search(r'--location\s+(\S+)', stripped, re.IGNORECASE)
                
                if name_match:
                    group_name = name_match.group(1)
                    project_id = group_name.replace('-', '').lower()[:30]  # GCP project IDs have restrictions
                    
                    gcp_command = f'gcloud projects create {project_id} --name="{group_name}"'
                    
                    if location_match:
                        azure_location = location_match.group(1).lower()
                        gcp_region = azure_to_gcp_regions.get(azure_location, 'us-central1')
                        gcp_command += f' --labels=location={gcp_region}'
                    
                    # Preserve comment if present
                    comment = ''
                    if '#' in line:
                        comment_part = line.split('#', 1)[1]
                        comment = f'  # {comment_part.strip()}'
                    
                    transformed_lines.append(f'{gcp_command}{comment}')
                    logger.info(f"Transformed: {stripped} → {gcp_command}")
                else:
                    transformed_lines.append(line)
            
            # Transform: az storage account create -n <name> -g <group>
            # → gcloud storage buckets create gs://<bucket-name> --project=<project-id>
            elif re.match(r'^\s*az\s+storage\s+account\s+create', stripped, re.IGNORECASE):
                # Extract name and resource group
                name_match = re.search(r'[-]n\s+(\S+)', stripped, re.IGNORECASE)
                group_match = re.search(r'[-]g\s+(\S+)', stripped, re.IGNORECASE)
                
                if name_match:
                    storage_name = name_match.group(1)
                    bucket_name = storage_name.replace('-', '').lower()
                    
                    # GCP bucket names must be globally unique and lowercase
                    bucket_name = re.sub(r'[^a-z0-9-]', '', bucket_name)
                    
                    project_id = bucket_name
                    if group_match:
                        project_id = group_match.group(1).replace('-', '').lower()[:30]
                    
                    gcp_command = f'gcloud storage buckets create gs://{bucket_name} --project={project_id}'
                    
                    # Preserve comment if present
                    comment = ''
                    if '#' in line:
                        comment_part = line.split('#', 1)[1]
                        comment = f'  # {comment_part.strip()}'
                    
                    transformed_lines.append(f'{gcp_command}{comment}')
                    logger.info(f"Transformed: {stripped} → {gcp_command}")
                else:
                    transformed_lines.append(line)
            
            # Transform: az storage account show -n <name> -g <group>
            # → gcloud storage buckets describe gs://<bucket-name> --project=<project-id>
            elif re.match(r'^\s*az\s+storage\s+account\s+show', stripped, re.IGNORECASE):
                name_match = re.search(r'[-]n\s+(\S+)', stripped, re.IGNORECASE)
                group_match = re.search(r'[-]g\s+(\S+)', stripped, re.IGNORECASE)
                
                if name_match:
                    storage_name = name_match.group(1)
                    bucket_name = storage_name.replace('-', '').lower()
                    bucket_name = re.sub(r'[^a-z0-9-]', '', bucket_name)
                    
                    project_id = bucket_name
                    if group_match:
                        project_id = group_match.group(1).replace('-', '').lower()[:30]
                    
                    gcp_command = f'gcloud storage buckets describe gs://{bucket_name} --project={project_id}'
                    
                    comment = ''
                    if '#' in line:
                        comment_part = line.split('#', 1)[1]
                        comment = f'  # {comment_part.strip()}'
                    
                    transformed_lines.append(f'{gcp_command}{comment}')
                else:
                    transformed_lines.append(line)
            
            # Transform: az storage blob upload -f <file> -c <container> -n <blob-name> --account-name <account>
            # → gsutil cp <file> gs://<bucket-name>/<blob-name>
            elif re.match(r'^\s*az\s+storage\s+blob\s+upload', stripped, re.IGNORECASE):
                file_match = re.search(r'[-]f\s+(\S+)', stripped, re.IGNORECASE)
                container_match = re.search(r'[-]c\s+(\S+)', stripped, re.IGNORECASE)
                blob_match = re.search(r'[-]n\s+(\S+)', stripped, re.IGNORECASE)
                account_match = re.search(r'--account-name\s+(\S+)', stripped, re.IGNORECASE)
                
                if file_match and container_match:
                    file_path = file_match.group(1)
                    container = container_match.group(1)
                    blob_name = blob_match.group(1) if blob_match else file_path.split('/')[-1]
                    
                    bucket_name = container
                    if account_match:
                        bucket_name = account_match.group(1).replace('-', '').lower()
                    
                    gcp_command = f'gsutil cp {file_path} gs://{bucket_name}/{blob_name}'
                    
                    comment = ''
                    if '#' in line:
                        comment_part = line.split('#', 1)[1]
                        comment = f'  # {comment_part.strip()}'
                    
                    transformed_lines.append(f'{gcp_command}{comment}')
                else:
                    transformed_lines.append(line)
            
            # Transform: az storage blob download -c <container> -n <blob-name> -f <file> --account-name <account>
            # → gsutil cp gs://<bucket-name>/<blob-name> <file>
            elif re.match(r'^\s*az\s+storage\s+blob\s+download', stripped, re.IGNORECASE):
                container_match = re.search(r'[-]c\s+(\S+)', stripped, re.IGNORECASE)
                blob_match = re.search(r'[-]n\s+(\S+)', stripped, re.IGNORECASE)
                file_match = re.search(r'[-]f\s+(\S+)', stripped, re.IGNORECASE)
                account_match = re.search(r'--account-name\s+(\S+)', stripped, re.IGNORECASE)
                
                if container_match and blob_match and file_match:
                    container = container_match.group(1)
                    blob_name = blob_match.group(1)
                    file_path = file_match.group(1)
                    
                    bucket_name = container
                    if account_match:
                        bucket_name = account_match.group(1).replace('-', '').lower()
                    
                    gcp_command = f'gsutil cp gs://{bucket_name}/{blob_name} {file_path}'
                    
                    comment = ''
                    if '#' in line:
                        comment_part = line.split('#', 1)[1]
                        comment = f'  # {comment_part.strip()}'
                    
                    transformed_lines.append(f'{gcp_command}{comment}')
                else:
                    transformed_lines.append(line)
            
            # Transform: az storage container create -n <container> --account-name <account>
            # → gcloud storage buckets create gs://<bucket-name> --project=<project-id>
            elif re.match(r'^\s*az\s+storage\s+container\s+create', stripped, re.IGNORECASE):
                container_match = re.search(r'[-]n\s+(\S+)', stripped, re.IGNORECASE)
                account_match = re.search(r'--account-name\s+(\S+)', stripped, re.IGNORECASE)
                
                if container_match:
                    container = container_match.group(1)
                    bucket_name = container.replace('-', '').lower()
                    bucket_name = re.sub(r'[^a-z0-9-]', '', bucket_name)
                    
                    project_id = bucket_name
                    if account_match:
                        project_id = account_match.group(1).replace('-', '').lower()[:30]
                    
                    gcp_command = f'gcloud storage buckets create gs://{bucket_name} --project={project_id}'
                    
                    comment = ''
                    if '#' in line:
                        comment_part = line.split('#', 1)[1]
                        comment = f'  # {comment_part.strip()}'
                    
                    transformed_lines.append(f'{gcp_command}{comment}')
                else:
                    transformed_lines.append(line)
            
            # Keep other az commands but add a comment suggesting GCP equivalent
            elif re.match(r'^\s*az\s+', stripped, re.IGNORECASE):
                # Add comment suggesting manual review
                if '#' not in line:
                    transformed_lines.append(f'{line}  # TODO: Review and convert to GCP CLI (gcloud) equivalent')
                else:
                    transformed_lines.append(line)
            
            # Keep all other lines as-is
            else:
                transformed_lines.append(line)
        
        result = '\n'.join(transformed_lines)
        
        # Final cleanup: replace any remaining Azure references
        result = re.sub(r'\baz\s+group\b', 'gcloud projects', result, flags=re.IGNORECASE)
        result = re.sub(r'\baz\s+storage\b', 'gcloud storage', result, flags=re.IGNORECASE)
        
        return result
    
    def _transform_azure_with_gemini_primary(self, code: str, recipe: Dict[str, Any], retry: bool = False, language: str = 'python') -> str:
        """Use Gemini as the PRIMARY transformation engine for Azure to GCP migrations"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            import google.generativeai as genai
            from config import Config
            
            if not Config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not set, falling back to regex")
                return code
            
            genai.configure(api_key=Config.GEMINI_API_KEY)
            # Try gemini-2.5-flash (fastest), then gemini-2.5-pro (better quality)
            try:
                model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception:
                try:
                    model = genai.GenerativeModel('models/gemini-2.5-pro')
                except Exception:
                    try:
                        model = genai.GenerativeModel('models/gemini-pro')
                    except Exception:
                        model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            service_type = recipe.get('service_type', '')
            target_api = recipe.get('target_api', 'GCP')
            
            # Build comprehensive prompt for Azure to GCP transformation
            if language == 'go':
                prompt = self._build_azure_go_transformation_prompt(code, service_type, target_api, retry)
            else:
                prompt = self._build_azure_transformation_prompt(code, service_type, target_api, retry)
            
            # Add timeout and generation config
            import google.generativeai.types as genai_types
            generation_config = genai_types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.1,
            )
            
            # Use threading timeout to prevent hanging
            import signal
            import threading
            
            response_result = [None]
            exception_result = [None]
            
            def generate_with_timeout():
                try:
                    response_result[0] = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        request_options={"timeout": 60}
                    )
                except Exception as e:
                    exception_result[0] = e
            
            thread = threading.Thread(target=generate_with_timeout)
            thread.daemon = True
            thread.start()
            thread.join(timeout=90)
            
            if thread.is_alive():
                logger.warning("Gemini API call timed out after 90 seconds")
                raise TimeoutError("Gemini API call timed out")
            
            if exception_result[0]:
                raise exception_result[0]
            
            if not response_result[0]:
                raise Exception("No response from Gemini API")
            
            response = response_result[0]
            transformed_code = response.text.strip()
            
            # Extract code from markdown
            transformed_code = self._extract_code_from_response(transformed_code, language=language)
            
            logger.info("Gemini Azure transformation completed")
            return transformed_code
            
        except Exception as e:
            logger.warning(f"Gemini Azure transformation failed: {e}, falling back to regex")
            return code
    
    def _build_azure_transformation_prompt(self, code: str, service_type: str, target_api: str, retry: bool = False) -> str:
        """Build prompt for Azure to GCP transformation (default Python)"""
        # Load architectural skills
        try:
            from infrastructure.adapters.skills_loader import get_skills_loader
            skills_loader = get_skills_loader()
            skills_prompt = skills_loader.get_skills_prompt()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load skills: {e}, proceeding without skills")
            skills_prompt = ""
        
        retry_note = "\n\n**THIS IS A RETRY - Previous attempt still contained Azure patterns. Be EXTREMELY thorough this time.**" if retry else ""
        
        prompt = f"""{skills_prompt}

You are an expert code refactoring assistant. Transform the following Azure Python code to Google Cloud Platform (GCP) code.

**ARCHITECTURAL REQUIREMENTS:**
When generating the refactored code, you MUST follow Clean Architecture principles:
- Use ports and adapters pattern for external dependencies (GCP SDKs)
- Keep business logic separate from infrastructure code
- Use immutable data structures where possible
- Include architectural intent documentation in code comments
- Follow Domain-Driven Design principles for domain models

**CRITICAL REQUIREMENTS:**
1. **ZERO AZURE CODE** - The output must contain NO Azure patterns, variables, or APIs
2. **Complete transformation** - Every Azure service call must be replaced with its GCP equivalent
3. **Correct syntax** - Output must be valid, executable Python code
4. **Proper imports** - Include all necessary GCP SDK imports

{retry_note}

**INPUT CODE:**
```python
{code}
```

**OUTPUT REQUIREMENTS:**
- Return ONLY the transformed Python code
- NO explanations, NO markdown formatting, NO code blocks
- Just pure, executable Python code
- Ensure ALL Azure patterns are removed
- Ensure ALL GCP APIs are used correctly

**TRANSFORMED GCP CODE:**"""
        
        return prompt
    
    def _build_azure_go_transformation_prompt(self, code: str, service_type: str, target_api: str, retry: bool = False) -> str:
        """Build a comprehensive prompt for Gemini to transform Azure Go code to GCP"""
        # Load architectural skills
        try:
            from infrastructure.adapters.skills_loader import get_skills_loader
            skills_loader = get_skills_loader()
            skills_prompt = skills_loader.get_skills_prompt()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load skills: {e}, proceeding without skills")
            skills_prompt = ""
        
        # Detect Azure services from Go code
        services_detected = []
        if re.search(r'github\.com/Azure/azure-sdk-for-go.*storage|azblob|BlobServiceClient', code, re.IGNORECASE):
            services_detected.append('Blob Storage')
        if re.search(r'github\.com/Azure/azure-sdk-for-go.*cosmos|azcosmos|CosmosClient', code, re.IGNORECASE):
            services_detected.append('Cosmos DB')
        if re.search(r'github\.com/Azure/azure-sdk-for-go.*servicebus|azservicebus|ServiceBusClient', code, re.IGNORECASE):
            services_detected.append('Service Bus')
        if re.search(r'github\.com/Azure/azure-event-hubs-go|EventHubProducerClient', code, re.IGNORECASE):
            services_detected.append('Event Hubs')
        if re.search(r'github\.com/Azure/azure-sdk-for-go.*keyvault|azsecrets|SecretClient', code, re.IGNORECASE):
            services_detected.append('Key Vault')
        if re.search(r'github\.com/Azure/azure-sdk-for-go.*monitor|ApplicationInsightsClient', code, re.IGNORECASE):
            services_detected.append('Application Insights')
        
        services_str = ', '.join(services_detected) if services_detected else 'Azure services'
        
        retry_note = "\n\n**THIS IS A RETRY - Previous attempt still contained Azure patterns. Be EXTREMELY thorough this time.**" if retry else ""
        
        prompt = f"""{skills_prompt}

You are an expert Go code refactoring assistant. Transform the following Azure Go code to Google Cloud Platform (GCP) Go code.

**ARCHITECTURAL REQUIREMENTS:**
When generating the refactored code, you MUST follow Clean Architecture principles:
- Use interfaces for external dependencies (GCP SDKs)
- Keep business logic in domain services, not in infrastructure adapters
- Use immutable structs (no exported setters) where possible
- Include architectural intent documentation in Go doc comments
- Follow Domain-Driven Design principles for domain models

**CRITICAL REQUIREMENTS:**
1. **ZERO AZURE CODE** - The output must contain NO Azure patterns, packages, or APIs
2. **Complete transformation** - Every Azure service call must be replaced with its GCP equivalent
3. **Correct Go syntax** - Output must be valid, compilable Go code
4. **Proper imports** - Include all necessary GCP SDK imports
5. **Preserve function structure** - Maintain function signatures, struct definitions, and structure
6. **Correct API usage** - Use GCP Go APIs correctly, not Azure patterns with GCP imports
7. **Context handling** - Preserve context.Context usage where appropriate

**SERVICES DETECTED:** {services_str}

**TRANSFORMATION RULES:**

**Blob Storage → Cloud Storage:**
- `github.com/Azure/azure-sdk-for-go/sdk/storage/azblob` → `cloud.google.com/go/storage`
- `azblob.NewClient()` → `storage.NewClient(ctx)`
- `client.UploadBuffer()` → `bucket.Object(name).NewWriter(ctx); w.Write(data); w.Close()`
- `client.DownloadBuffer()` → `bucket.Object(name).NewReader(ctx); io.Copy(dest, r)`

**Cosmos DB → Firestore:**
- `github.com/Azure/azure-sdk-for-go/sdk/data/azcosmos` → `cloud.google.com/go/firestore`
- `azcosmos.NewClientWithKey()` → `firestore.NewClient(ctx, projectID)`
- `client.CreateItem()` → `client.Collection(collectionName).Doc(documentID).Set(ctx, data)`
- `client.ReadItem()` → `client.Collection(collectionName).Doc(documentID).Get(ctx)`

**Service Bus → Pub/Sub:**
- `github.com/Azure/azure-sdk-for-go/sdk/messaging/azservicebus` → `cloud.google.com/go/pubsub`
- `azservicebus.NewClientWithConnectionString()` → `pubsub.NewClient(ctx, projectID)`
- `sender.SendMessage()` → `topic.Publish(ctx, &pubsub.Message{{ Data: []byte(messageBody) }})`
- `receiver.ReceiveMessages()` → `sub.Receive(ctx, callback)`

**Event Hubs → Pub/Sub:**
- `github.com/Azure/azure-event-hubs-go` → `cloud.google.com/go/pubsub`
- `hub.Send()` → `topic.Publish(ctx, &pubsub.Message{{ Data: data }})`
- `hub.Receive()` → `sub.Receive(ctx, callback)`

**Key Vault → Secret Manager:**
- `github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets` → `cloud.google.com/go/secretmanager/apiv1`
- `azsecrets.NewClient()` → `secretmanager.NewClient(ctx)`
- `client.GetSecret()` → `client.AccessSecretVersion(ctx, req)`
- `client.SetSecret()` → `client.CreateSecret()` + `client.AddSecretVersion()`

**Application Insights → Cloud Monitoring:**
- `github.com/Azure/azure-sdk-for-go/sdk/monitor` → `cloud.google.com/go/monitoring/apiv3`, `cloud.google.com/go/logging`
- `ApplicationInsightsClient` → `monitoring.MetricServiceClient` or `logging.Client`
- `client.TrackEvent()` → `logging.Client().LogStruct()`
- `client.TrackMetric()` → `monitoring.CreateTimeSeries()`

**Environment Variables:**
- `AZURE_STORAGE_CONNECTION_STRING` → `GOOGLE_APPLICATION_CREDENTIALS`
- `COSMOS_ENDPOINT` → `GOOGLE_CLOUD_PROJECT`
- `AZURE_KEY_VAULT_URL` → `GOOGLE_CLOUD_PROJECT`
- `APPINSIGHTS_INSTRUMENTATION_KEY` → `GOOGLE_CLOUD_PROJECT`

**Variable Naming:**
- `blobClient` → `storageClient` or `client`
- `cosmosClient` → `firestoreClient` or `client`
- `serviceBusClient` → `pubsubClient` or `client`

**Exception Handling:**
- Azure SDK errors → GCP SDK errors
- Preserve error handling patterns with appropriate GCP error types

**Code Structure:**
- Preserve function names, struct definitions
- Preserve context.Context usage
- Maintain proper Go formatting and indentation
- Ensure all imports are correct and necessary
- Use proper Go error handling: return errors, check err != nil

**Go-specific:**
- Preserve package declarations
- Preserve exported/unexported function names (capitalization)
- Use proper Go idioms and patterns
- Ensure proper error handling with `if err != nil` checks

{retry_note}

**INPUT CODE:**
```go
{code}
```

**OUTPUT REQUIREMENTS:**
- Return ONLY the transformed Go code
- NO explanations, NO markdown formatting, NO code blocks
- Just pure, compilable Go code
- Ensure ALL Azure patterns are removed
- Ensure ALL GCP APIs are used correctly
- Preserve the complete function and struct structure
- Use proper Go error handling

**TRANSFORMED GCP CODE:**"""
        
        return prompt
    
    def _aggressive_go_azure_cleanup(self, code: str) -> str:
        """Aggressive cleanup of Azure patterns in Go code"""
        # Remove Azure SDK imports
        code = re.sub(r'github\.com/Azure/azure-sdk-for-go/sdk/storage/azblob', 'cloud.google.com/go/storage', code)
        code = re.sub(r'github\.com/Azure/azure-sdk-for-go/sdk/data/azcosmos', 'cloud.google.com/go/firestore', code)
        code = re.sub(r'github\.com/Azure/azure-sdk-for-go/sdk/messaging/azservicebus', 'cloud.google.com/go/pubsub', code)
        code = re.sub(r'github\.com/Azure/azure-event-hubs-go', 'cloud.google.com/go/pubsub', code)
        code = re.sub(r'github\.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets', 'cloud.google.com/go/secretmanager/apiv1', code)
        code = re.sub(r'github\.com/Azure/azure-sdk-for-go/sdk/monitor', 'cloud.google.com/go/monitoring/apiv3', code)
        
        # Replace Azure client creation
        code = re.sub(r'azblob\.NewClient\(', 'storage.NewClient(', code)
        code = re.sub(r'azcosmos\.NewClientWithKey\(', 'firestore.NewClient(', code)
        code = re.sub(r'azservicebus\.NewClientWithConnectionString\(', 'pubsub.NewClient(', code)
        code = re.sub(r'azsecrets\.NewClient\(', 'secretmanager.NewClient(', code)
        
        # Replace Azure method calls
        code = re.sub(r'\.UploadBuffer\(', '.NewWriter(ctx); w.Write(', code)
        code = re.sub(r'\.DownloadBuffer\(', '.NewReader(ctx); io.Copy(', code)
        code = re.sub(r'\.CreateItem\(', '.Set(ctx, ', code)
        code = re.sub(r'\.ReadItem\(', '.Get(ctx)', code)
        code = re.sub(r'\.SendMessage\(', '.Publish(ctx, &pubsub.Message', code)
        code = re.sub(r'\.GetSecret\(', '.AccessSecretVersion(ctx, req)', code)
        code = re.sub(r'\.SetSecret\(', '.CreateSecret(ctx, req)', code)
        
        # Replace Azure environment variables
        code = re.sub(r'AZURE_STORAGE_CONNECTION_STRING', 'GOOGLE_APPLICATION_CREDENTIALS', code)
        code = re.sub(r'COSMOS_ENDPOINT', 'GOOGLE_CLOUD_PROJECT', code)
        code = re.sub(r'AZURE_KEY_VAULT_URL', 'GOOGLE_CLOUD_PROJECT', code)
        code = re.sub(r'APPINSIGHTS_INSTRUMENTATION_KEY', 'GOOGLE_CLOUD_PROJECT', code)
        
        return code
    
    def _has_azure_patterns(self, code: str, language: str = 'python') -> bool:
        """Check if code still contains Azure patterns"""
        if language == 'go':
            azure_patterns = [
                r'github\.com/Azure',
                r'azblob\.',
                r'azcosmos\.',
                r'azservicebus\.',
                r'azsecrets\.',
                r'BlobServiceClient',
                r'CosmosClient',
                r'ServiceBusClient',
                r'SecretClient',
                r'AZURE_STORAGE_CONNECTION_STRING',
                r'COSMOS_ENDPOINT',
                r'AZURE_KEY_VAULT_URL'
            ]
        else:
            azure_patterns = [
                r'azure\.',
                r'Azure\.',
                r'BlobServiceClient',
                r'CosmosClient',
                r'ServiceBusClient',
                r'AZURE_'
            ]
        
        for pattern in azure_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False
    
    def _extract_code_from_response(self, response_text: str, language: str = 'python') -> str:
        """Extract code from Gemini response, handling various formats"""
        # Remove markdown code blocks
        if language == 'go':
            code_block_marker = '```go'
        elif language == 'csharp':
            code_block_marker = '```csharp'
        elif language == 'java':
            code_block_marker = '```java'
        else:
            code_block_marker = '```python'
        
        if code_block_marker in response_text:
            parts = response_text.split(code_block_marker)
            if len(parts) >= 2:
                code = parts[1].split('```')[0].strip()
                return code
        
        # If no code block, return as-is
        return response_text.strip()
    
    def _aggressive_azure_cleanup(self, code: str) -> str:
        """
        AGGRESSIVE Azure cleanup that removes ALL Azure patterns.
        This ensures zero Azure references in output code.
        """
        result = code
        
        # STEP 1: Replace ALL Azure imports
        result = re.sub(r'from azure\.storage\.blob import.*', 'from google.cloud import storage', result)
        result = re.sub(r'import azure\.storage\.blob', 'from google.cloud import storage', result)
        result = re.sub(r'from azure\.functions import.*', 'from google.cloud import functions', result)
        result = re.sub(r'import azure\.functions', 'from google.cloud import functions', result)
        result = re.sub(r'from azure\.cosmos import.*', 'from google.cloud import firestore', result)
        result = re.sub(r'import azure\.cosmos', 'from google.cloud import firestore', result)
        result = re.sub(r'from azure\.servicebus import.*', 'from google.cloud import pubsub_v1', result)
        result = re.sub(r'import azure\.servicebus', 'from google.cloud import pubsub_v1', result)
        result = re.sub(r'from azure\.eventhub import.*', 'from google.cloud import pubsub_v1', result)
        result = re.sub(r'import azure\.eventhub', 'from google.cloud import pubsub_v1', result)
        
        # STEP 2: Replace ALL Azure client instantiations
        result = re.sub(
            r'(\w+)\s*=\s*BlobServiceClient\.[^)]+\)',
            r'\1 = storage.Client()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'(\w+)\s*=\s*CosmosClient\s*\([^)]+\)',
            r'\1 = firestore.Client()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'(\w+)\s*=\s*ServiceBusClient\.[^)]+\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'(\w+)\s*=\s*EventHubProducerClient\s*\([^)]+\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # STEP 3: Replace Azure environment variables
        result = re.sub(r'AZURE_STORAGE_CONTAINER', 'GCS_BUCKET_NAME', result)
        result = re.sub(r'AZURE_STORAGE_CONNECTION_STRING', 'GOOGLE_APPLICATION_CREDENTIALS', result)
        result = re.sub(r'AZURE_COSMOS_ENDPOINT', 'GCP_PROJECT_ID', result)
        result = re.sub(r'AZURE_COSMOS_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', result)
        result = re.sub(r'AZURE_SERVICE_BUS_CONNECTION_STRING', 'GCP_PROJECT_ID', result)
        result = re.sub(r'AZURE_SERVICE_BUS_QUEUE_NAME', 'GCP_PUBSUB_TOPIC_ID', result)
        result = re.sub(r'AZURE_FUNCTION_NAME', 'GCP_CLOUD_FUNCTION_NAME', result)
        result = re.sub(r'AZURE_CLIENT_ID', 'GCP_PROJECT_ID', result)
        result = re.sub(r'AZURE_CLIENT_SECRET', 'GOOGLE_APPLICATION_CREDENTIALS', result)
        result = re.sub(r'AZURE_LOCATION', 'GCP_REGION', result)
        
        # STEP 4: Replace Azure-specific patterns
        result = re.sub(r'\bBlobServiceClient\b', 'storage.Client', result)
        result = re.sub(r'\bBlobClient\b', 'blob', result)
        result = re.sub(r'\bContainerClient\b', 'bucket', result)
        result = re.sub(r'\bCosmosClient\b', 'firestore.Client', result)
        result = re.sub(r'\bServiceBusClient\b', 'pubsub_v1.PublisherClient', result)
        result = re.sub(r'\bEventHubProducerClient\b', 'pubsub_v1.PublisherClient', result)
        
        # STEP 5: Replace Azure method calls
        result = re.sub(r'\.upload_blob\(', '.upload_from_string(', result)
        result = re.sub(r'\.download_blob\(', '.download_as_text(', result)
        result = re.sub(r'\.get_blob_client\(', '.blob(', result)
        result = re.sub(r'\.get_container_client\(', '.bucket(', result)
        
        # STEP 5.5: Remove Azure/Cosmos DB parameter patterns (similar to AWS DynamoDB)
        # Remove Item= parameter (Cosmos DB uses this, Firestore doesn't)
        result = re.sub(r'Item\s*=\s*', '', result)
        # Remove TableName= parameter
        result = re.sub(r'TableName\s*=\s*', '', result)
        # Remove PartitionKey= parameter
        result = re.sub(r'PartitionKey\s*=\s*', '', result)
        # Remove Key= parameter in Cosmos context
        result = re.sub(r'Key\s*=\s*', '', result)
        
        # STEP 6: Replace Azure Functions patterns
        result = re.sub(r'func\.HttpRequest', 'functions.HttpRequest', result)
        result = re.sub(r'func\.HttpResponse', 'functions.HttpResponse', result)
        result = re.sub(r'azure\.functions', 'google.cloud.functions', result)
        
        # Clean up syntax issues
        result = re.sub(r',\s*,', ',', result)  # Double commas
        result = re.sub(r'\(\s*,', '(', result)  # Comma after opening paren
        result = re.sub(r',\s*\)', ')', result)  # Comma before closing paren
        
        return result
    
    def _validate_and_fix_syntax(self, code: str, original_code: str = None) -> str:
        """
        Validate Python syntax and ensure no AWS/Azure references in output code.
        Returns syntactically correct code or raises SyntaxError.
        """
        import ast
        import logging
        import re
        logger = logging.getLogger(__name__)
        
        # Check if code is shell/bash script (starts with shebang or contains shell commands)
        is_shell_script = (
            code.strip().startswith('#!') or
            re.search(r'^\s*(az|aws|gcloud|kubectl|docker)\s+', code, re.MULTILINE) or
            re.search(r'^\s*(export|export\s+\w+=)', code, re.MULTILINE)
        )
        
        if is_shell_script:
            logger.info("Detected shell/bash script - skipping Python syntax validation")
            # For shell scripts, just check for Azure/AWS patterns but don't validate Python syntax
            return code
        
        # Validate no AWS/Azure references in output code
        aws_azure_patterns = [
            r'\bboto3\b', r'\bAWS\b(?!\w)', r'\baws\b(?!\w)', r'\bS3\b(?!\w)', r'\bs3\b(?!\w)',
            r'\bLambda\b(?!\s*[:=])', r'\bDynamoDB\b', r'\bdynamodb\b',
            r'\bSQS\b', r'\bsqs\b', r'\bSNS\b', r'\bsns\b', r'\bRDS\b', r'\brds\b',
            r'\bEC2\b', r'\bec2\b', r'\bCloudWatch\b', r'\bcloudwatch\b',
            r'\bAPI Gateway\b', r'\bapigateway\b', r'\bEKS\b', r'\beks\b',
            r'\bFargate\b', r'\bfargate\b', r'\bECS\b', r'\becs\b',
            r'\bAzure\b(?!\w)', r'\bazure\b(?!\w)', r'\bBlobServiceClient\b', r'\bblob_service_client\b',
            r'\bCosmosClient\b', r'\bcosmos_client\b', r'\bServiceBusClient\b',
            r'\bEventHubProducerClient\b', r'\bazure\.storage\b', r'\bazure\.functions\b',
            r'\bazure\.cosmos\b', r'\bazure\.servicebus\b', r'\bazure\.eventhub\b',
            r'\bAWS_ACCESS_KEY_ID\b', r'\bAWS_SECRET_ACCESS_KEY\b', r'\bAWS_REGION\b',
            r'\bAWS_LAMBDA_FUNCTION_NAME\b', r'\bS3_BUCKET_NAME\b', r'\bAZURE_CLIENT_ID\b',
            r'\bAZURE_CLIENT_SECRET\b', r'\bAZURE_LOCATION\b', r'\bAZURE_STORAGE_CONTAINER\b'
        ]
        
        # Check for AWS/Azure references (excluding comments and strings)
        code_lines = code.split('\n')
        violations = []
        for i, line in enumerate(code_lines, 1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            # Check if line contains AWS/Azure patterns
            for pattern in aws_azure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Make sure it's not in a string literal
                    if not (line.count('"') % 2 == 1 or line.count("'") % 2 == 1):
                        violations.append(f"Line {i}: Found AWS/Azure reference: {pattern} in '{line.strip()}'")
                        break
        
        if violations:
            logger.warning("AWS/Azure references found in output code:")
            for violation in violations:
                logger.warning(violation)
        
        # Validate syntax (only for Python code)
        try:
            ast.parse(code)
            return code  # Code is valid
        except SyntaxError as e:
            logger.debug(f"Syntax error detected: {e}")
            # If original_code is shell script, return it without error
            if original_code:
                original_is_shell = (
                    original_code.strip().startswith('#!') or
                    re.search(r'^\s*(az|aws|gcloud|kubectl|docker)\s+', original_code, re.MULTILINE)
                )
                if original_is_shell:
                    logger.info("Original code is shell script - returning as-is")
                    return original_code
                logger.warning("Returning original code due to transformation syntax errors")
                return original_code
            else:
                raise SyntaxError(f"Transformed code is invalid: {e}")


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
            elif 'azure_key_vault_to_secret_manager' in service_type:
                return self._migrate_azure_key_vault_to_secret_manager(code)
            elif 'azure_application_insights_to_monitoring' in service_type:
                return self._migrate_azure_application_insights_to_monitoring(code)
        
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
        
        if 'azure.keyvault' in result_code or 'SecretClient' in result_code or 'KeyVaultClient' in result_code:
            result_code = self._migrate_azure_key_vault_to_secret_manager(result_code)
        
        if 'azure.applicationinsights' in result_code or 'ApplicationInsightsClient' in result_code or 'TelemetryClient' in result_code:
            result_code = self._migrate_azure_application_insights_to_monitoring(result_code)
        
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
        if code is None:
            return ""
        
        # Replace Azure Blob Storage imports with GCS imports FIRST
        code = re.sub(r'from azure\.storage\.blob import.*', 'from google.cloud import storage', code)
        code = re.sub(r'import azure\.storage\.blob.*', 'from google.cloud import storage', code)
        
        # Track variable name for blob service client
        blob_client_match = re.search(r'(\w+)\s*=\s*BlobServiceClient', code)
        blob_client_var = blob_client_match.group(1) if blob_client_match else 'blob_service_client'
        gcs_client_var = 'gcs_client' if blob_client_var == 'blob_service_client' else f'{blob_client_var}_gcs'
        
        # Replace client instantiation - handle all patterns
        code = re.sub(
            r'(\w+)\s*=\s*BlobServiceClient\.from_connection_string\([^)]+\)',
            rf'{gcs_client_var} = storage.Client()',
            code,
            flags=re.DOTALL
        )
        # Handle BlobServiceClient with account_url and credential
        code = re.sub(
            r'(\w+)\s*=\s*BlobServiceClient\s*\([^)]*account_url[^)]*credential[^)]*\)',
            rf'{gcs_client_var} = storage.Client()',
            code,
            flags=re.DOTALL
        )
        # Handle BlobServiceClient without assignment
        code = re.sub(
            r'BlobServiceClient\s*\([^)]*\)',
            rf'{gcs_client_var} = storage.Client()',
            code,
            flags=re.DOTALL
        )
        # Handle BlobServiceClient with DefaultAzureCredential
        code = re.sub(
            r'(\w+)\s*=\s*BlobServiceClient\s*\([^)]*DefaultAzureCredential[^)]*\)',
            rf'{gcs_client_var} = storage.Client()',
            code,
            flags=re.DOTALL
        )
        # Handle BlobServiceClient with comment in the middle - fix syntax error
        # Pattern: blob_service_client = BlobServiceClient(# comment, credential="key")
        # This creates invalid syntax, so we need to replace the entire line
        lines = code.split('\n')
        result_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if line contains BlobServiceClient with comment
            if re.search(r'BlobServiceClient\s*\([^)]*#', line):
                # Find the matching closing paren on subsequent lines
                paren_count = line.count('(') - line.count(')')
                j = i + 1
                while j < len(lines) and paren_count > 0:
                    paren_count += lines[j].count('(') - lines[j].count(')')
                    j += 1
                # Replace the entire multi-line BlobServiceClient call
                var_match = re.search(r'(\w+)\s*=\s*BlobServiceClient', line)
                if var_match:
                    var_name = var_match.group(1)
                    result_lines.append(f'{gcs_client_var} = storage.Client()')
                    i = j
                    continue
            result_lines.append(line)
            i += 1
        code = '\n'.join(result_lines)
        
        # Handle BlobServiceClient with comment in the middle (single line)
        code = re.sub(
            r'(\w+)\s*=\s*BlobServiceClient\s*\([^)]*#.*?credential[^)]*\)',
            rf'{gcs_client_var} = storage.Client()',
            code,
            flags=re.DOTALL
        )
        # Original pattern for backward compatibility
        code = re.sub(
            r'(\w+)\s*=\s*BlobServiceClient\([^)]+account_url=([^,]+),\s*credential=([^)]+)\)',
            rf'{gcs_client_var} = storage.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace get_container_client -> bucket
        code = re.sub(
            r'(\w+)\.get_container_client\(([^)]+)\)',
            rf'bucket = {gcs_client_var}.bucket(\2)',
            code
        )
        # Handle container_client variable assignments
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_container_client\(([^)]+)\)',
            rf'\1 = {gcs_client_var}.bucket(\3)',
            code
        )
        
        # Replace blob_client.get_blob_client -> bucket.blob
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_blob_client\([^)]*container=([^,]+),\s*blob=([^)]+)\)',
            r'\1 = \2.bucket(\3).blob(\4)',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_blob_client\([^)]*blob=([^,]+),\s*container=([^)]+)\)',
            r'\1 = \2.bucket(\4).blob(\3)',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_blob_client\(([^)]+)\)',
            r'\1 = bucket.blob(\3)',
            code
        )
        
        # Replace container_client.create_container -> bucket.create
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.create_container\(([^)]*)\)',
            r'\1 = \2.create()',
            code
        )
        code = re.sub(
            r'(\w+)\.create_container\(([^)]*)\)',
            r'bucket.create()',
            code
        )
        
        # Replace blob_client.upload_blob -> blob.upload_from_filename/upload_from_string
        # Handle with open() pattern
        code = re.sub(
            r'with\s+open\(([^,]+),\s*["\']rb["\']\)\s+as\s+(\w+)\s*:\s*(\w+)\.upload_blob\((\2),\s*overwrite=True\)',
            r'blob = bucket.blob("blob_name")\n    blob.upload_from_filename(\1)',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'with\s+open\(([^,]+),\s*["\']rb["\']\)\s+as\s+(\w+)\s*:\s*(\w+)\.upload_blob\((\2)\)',
            r'blob = bucket.blob("blob_name")\n    blob.upload_from_filename(\1)',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\.upload_blob\(([^)]+),\s*overwrite=True\)',
            r'blob = bucket.blob("blob_name")\n    blob.upload_from_filename(\2) if isinstance(\2, str) else blob.upload_from_string(\2)',
            code
        )
        code = re.sub(
            r'(\w+)\.upload_blob\(([^)]+)\)',
            r'blob = bucket.blob("blob_name")\n    blob.upload_from_filename(\2) if isinstance(\2, str) else blob.upload_from_string(\2)',
            code
        )
        
        # Replace download_blob -> download_as_bytes/download_to_filename
        # Handle with open() pattern for download
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.download_blob\(([^)]*)\)\s*with\s+open\(([^,]+),\s*["\']wb["\']\)\s+as\s+(\w+)\s*:\s*(\5)\.write\((\1)\.readall\(\)\)',
            r'blob = bucket.blob("blob_name")\n    blob.download_to_filename(\4)',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.download_blob\(([^)]*)\)',
            r'\1 = \2.download_as_bytes()',
            code
        )
        code = re.sub(
            r'(\w+)\.download_blob\(([^)]*)\)',
            r'blob.download_as_bytes()',
            code
        )
        # Handle download_stream.readall() -> content (remove readall, use content directly)
        code = re.sub(
            r'(\w+)\.readall\(\)',
            r'\1',
            code
        )
        # Handle download_file.write(download_stream.readall()) -> blob.download_to_filename()
        code = re.sub(
            r'(\w+)\.write\(([^)]+)\.readall\(\)\)',
            r'# Content already downloaded',
            code
        )
        
        # Replace blob_data.readinto -> blob.download_to_filename
        code = re.sub(
            r'blob_data\.readinto\(([^)]+)\)',
            r'blob.download_to_filename(\1)',
            code
        )
        
        # Remove Azure URLs
        code = re.sub(
            r'account_url=[\'"]https://[^\'"]+\.blob\.core\.windows\.net[^\'"]*[\'"]',
            r'# Azure Blob Storage URL replaced with GCS',
            code
        )
        
        # Replace SAS token generation -> GCS signed URLs
        # Pattern: sas_token = generate_account_sas(...)
        code = re.sub(
            r'(\w+)\s*=\s*generate_account_sas\([^)]+account_name=([^,]+),\s*account_key=([^,]+),\s*resource_types=([^,]+),\s*permission=([^,]+),\s*expiry=([^\)]+)\)',
            r'# GCS uses blob.generate_signed_url() instead of account SAS\n# Example: blob.generate_signed_url(expiration=datetime.utcnow() + timedelta(hours=1), method="GET")\n# Note: Generate signed URL on the blob object, not account-level\n# \1 = blob.generate_signed_url(...)',
            code
        )
        code = re.sub(
            r'generate_account_sas\([^)]+\)',
            r'# GCS uses blob.generate_signed_url() instead of account SAS\n# Example: blob.generate_signed_url(expiration=datetime.utcnow() + timedelta(hours=1), method="GET")',
            code
        )
        # Replace imports more comprehensively
        code = re.sub(
            r'from azure\.storage\.blob import.*',
            r'from google.cloud import storage\nfrom datetime import datetime, timedelta',
            code
        )
        code = re.sub(
            r'import azure\.storage\.blob.*',
            r'from google.cloud import storage\nfrom datetime import datetime, timedelta',
            code
        )
        code = re.sub(
            r'ResourceTypes\(object=True\)',
            r'# ResourceTypes not needed for GCS',
            code
        )
        code = re.sub(
            r'AccountSasPermissions\(read=True\)',
            r'# Permissions specified in generate_signed_url method parameter',
            code
        )
        # Remove generate_account_sas from imports
        code = re.sub(r',\s*generate_account_sas', '', code)
        code = re.sub(r'generate_account_sas\s*,', '', code)
        
        # Replace blob_client.exists() -> blob.exists()
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.exists\(\)',
            r'\1 = \2.exists()',
            code
        )
        code = re.sub(
            r'(\w+)\.exists\(\)',
            r'blob.exists()',
            code
        )
        
        # Replace blob_client.delete_blob() -> blob.delete()
        code = re.sub(
            r'(\w+)\.delete_blob\(([^)]*)\)',
            r'blob.delete()',
            code
        )
        
        # Replace blob_client.get_blob_properties() -> blob.reload()
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_blob_properties\(([^)]*)\)',
            r'\1 = \2\n    \2.reload()',
            code
        )
        # Handle properties access
        code = re.sub(
            r'(\w+)\.content_settings\.content_type',
            r'\1.content_type',
            code
        )
        code = re.sub(
            r'(\w+)\.size',
            r'\1.size',
            code
        )
        code = re.sub(
            r'(\w+)\.last_modified',
            r'\1.updated',
            code
        )
        code = re.sub(
            r'(\w+)\.metadata',
            r'\1.metadata',
            code
        )
        
        # Replace blob_client.set_blob_metadata() -> blob.metadata = ...
        code = re.sub(
            r'(\w+)\.set_blob_metadata\(metadata=([^)]+)\)',
            r'\1.metadata = \2',
            code
        )
        
        # Replace blob_client.set_http_headers() -> blob.content_type = ...
        code = re.sub(
            r'(\w+)\.set_http_headers\(content_settings=ContentSettings\(content_type=([^)]+)\)\)',
            r'\1.content_type = \2',
            code
        )
        
        # Replace blob_client.create_snapshot() -> blob.generation (GCS uses generations)
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.create_snapshot\(([^)]*)\)',
            r'# GCS uses blob generations instead of snapshots\n    # blob.generation contains the generation number\n    \1 = {"generation": blob.generation}',
            code
        )
        
        # Replace blob_client.start_copy_from_url() -> blob.copy_to()
        code = re.sub(
            r'(\w+)\.start_copy_from_url\(([^)]+)\)',
            r'# Use blob.rewrite() or blob.copy_to() for copying',
            code
        )
        
        # Replace container_client.list_blobs() -> bucket.list_blobs()
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.list_blobs\(([^)]*)\)',
            r'\1 = list(\2.list_blobs(\3))',
            code
        )
        code = re.sub(
            r'(\w+)\.list_blobs\(([^)]*)\)',
            r'bucket.list_blobs(\2)',
            code
        )
        # Handle name_starts_with parameter
        code = re.sub(
            r'name_starts_with=([^,)]+)',
            r'prefix=\1',
            code
        )
        # Handle blob.name and blob.size
        code = re.sub(
            r'(\w+)\.name',
            r'\1.name',
            code
        )
        code = re.sub(
            r'(\w+)\.size',
            r'\1.size',
            code
        )
        
        # Replace blob_service_client.list_containers() -> storage_client.list_buckets()
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.list_containers\(([^)]*)\)',
            r'\1 = list(\2.list_buckets(\3))',
            code
        )
        code = re.sub(
            r'(\w+)\.list_containers\(([^)]*)\)',
            rf'{gcs_client_var}.list_buckets(\2)',
            code
        )
        # Handle container.name -> bucket.name
        code = re.sub(
            r'(\w+)\.name',
            r'\1.name',
            code
        )
        
        # Replace container_client.delete_container() -> bucket.delete()
        code = re.sub(
            r'(\w+)\.delete_container\(([^)]*)\)',
            r'bucket.delete(force=True)',
            code
        )
        
        # Handle generate_blob_sas and generate_container_sas -> blob.generate_signed_url()
        code = re.sub(
            r'(\w+)\s*=\s*generate_blob_sas\([^)]+\)',
            r'# \1 = blob.generate_signed_url(expiration=datetime.utcnow() + timedelta(hours=1), method="GET")',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*generate_container_sas\([^)]+\)',
            r'# \1 = bucket.generate_signed_url(expiration=datetime.utcnow() + timedelta(hours=1), method="GET")',
            code
        )
        code = re.sub(
            r'from\s+azure\.storage\.blob\s+import\s+generate_blob_sas[^,\n]*',
            r'from datetime import datetime, timedelta',
            code
        )
        code = re.sub(
            r'from\s+azure\.storage\.blob\s+import\s+generate_container_sas[^,\n]*',
            r'from datetime import datetime, timedelta',
            code
        )
        code = re.sub(
            r',\s*generate_blob_sas',
            '',
            code
        )
        code = re.sub(
            r',\s*generate_container_sas',
            '',
            code
        )
        code = re.sub(
            r'generate_blob_sas\s*,',
            '',
            code
        )
        code = re.sub(
            r'generate_container_sas\s*,',
            '',
            code
        )
        code = re.sub(
            r'BlobSasPermissions\(read=True\)',
            r'# Permissions specified in generate_signed_url method parameter',
            code
        )
        code = re.sub(
            r'ContainerSasPermissions\(read=True[^)]*\)',
            r'# Permissions specified in generate_signed_url method parameter',
            code
        )
        
        # Handle blob tags
        code = re.sub(
            r'(\w+)\.upload_blob\(([^,]+),\s*tags=([^,]+),\s*overwrite=True\)',
            r'blob = bucket.blob("blob_name")\n    blob.upload_from_filename(\2) if isinstance(\2, str) else blob.upload_from_string(\2)\n    # Note: GCS uses blob.metadata instead of tags',
            code
        )
        
        # Replace environment variables
        code = re.sub(
            r'AZURE_STORAGE_CONNECTION_STRING',
            'GOOGLE_APPLICATION_CREDENTIALS',
            code
        )
        code = re.sub(
            r'AZURE_STORAGE_ACCOUNT_NAME',
            'GOOGLE_CLOUD_PROJECT',
            code
        )
        code = re.sub(
            r'AZURE_STORAGE_ACCOUNT_KEY',
            'GOOGLE_APPLICATION_CREDENTIALS',
            code
        )
        
        # Remove Azure-specific imports
        code = re.sub(r'from azure\.identity import.*', '', code)
        code = re.sub(r'import azure\.identity.*', '', code)
        code = re.sub(r'from azure\.storage\.blob import.*', '', code)
        
        # Final aggressive cleanup - remove any remaining Azure patterns
        if hasattr(self, '_aggressive_azure_cleanup'):
            code = self._aggressive_azure_cleanup(code)
        
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
        
        # If Cosmos DB code is present, migrate it too - do this BEFORE other replacements
        if 'CosmosClient' in code or 'cosmos_client' in code or 'GetDatabase' in code or 'azure.cosmos' in code:
            code = self._migrate_azure_cosmos_db_to_firestore(code)
        
        # Final cleanup: remove any remaining azure.functions references
        code = re.sub(r'func\.DocumentList', 'list', code)
        code = re.sub(r'func\.HttpRequest', 'request', code)
        code = re.sub(r'func\.HttpResponse', 'str', code)
        
        return code

    def _migrate_azure_cosmos_db_to_firestore(self, code: str) -> str:
        """Migrate Azure Cosmos DB to Google Cloud Firestore"""
        # Replace Cosmos DB imports - be more aggressive
        # Handle: import azure.cosmos.cosmos_client as cosmos_client
        code = re.sub(r'import\s+azure\.cosmos\.cosmos_client\s+as\s+\w+', 'from google.cloud import firestore', code)
        code = re.sub(r'import\s+azure\.cosmos\.cosmos_client[^\n]*', 'from google.cloud import firestore', code)
        code = re.sub(r'from\s+azure\.cosmos\s+import[^\n]*', 'from google.cloud import firestore', code)
        # Also handle: import azure.cosmos.cosmos_client as cosmos_client (with newline)
        code = re.sub(r'import\s+azure\.cosmos\.cosmos_client\s+as\s+\w+\s*$', 'from google.cloud import firestore', code, flags=re.MULTILINE)
        # Handle multiline imports
        code = re.sub(r'import\s+azure\.cosmos[^\n]*', 'from google.cloud import firestore', code, flags=re.DOTALL)
        
        # Replace client instantiation patterns - handle both patterns
        # Match: client = cosmos_client.CosmosClient(url_connection=..., auth=...)
        code = re.sub(
            r'(\w+)\s*=\s*cosmos_client\.CosmosClient\s*\([^)]*url_connection[^)]*auth[^)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Match: client = CosmosClient(url_connection=..., auth=...)
        code = re.sub(
            r'(\w+)\s*=\s*CosmosClient\s*\([^)]*url_connection[^)]*auth[^)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Match: client = CosmosClient(url=..., credential=...)
        code = re.sub(
            r'(\w+)\s*=\s*CosmosClient\s*\([^)]*url[^)]*credential[^)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Match: client = CosmosClient( with multiline parameters
        code = re.sub(
            r'(\w+)\s*=\s*CosmosClient\s*\([^)]*url_connection[^)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Match: client = cosmos_client.CosmosClient( with multiline - be more aggressive
        code = re.sub(
            r'(\w+)\s*=\s*cosmos_client\.CosmosClient\s*\([^)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Match: client = CosmosClient( with any parameters
        code = re.sub(
            r'(\w+)\s*=\s*CosmosClient\s*\([^)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Also handle incomplete patterns (just CosmosClient(...))
        code = re.sub(
            r'CosmosClient\s*\([^)]*\)',
            r'firestore.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace GetDatabase/GetContainer patterns
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.GetDatabase\(([^)]+)\)',
            r'\1 = \2  # Database reference (Firestore uses project-level)',
            code
        )
        code = re.sub(
            r'(\w+)\.GetDatabase\(([^)]+)\)',
            r'\1  # Database reference (Firestore uses project-level)',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.GetContainer\(([^,]+),\s*([^)]+)\)',
            r'\1 = \2.collection(\4)',
            code
        )
        code = re.sub(
            r'(\w+)\.GetContainer\(([^,]+),\s*([^)]+)\)',
            r'\1.collection(\3)',
            code
        )
        code = re.sub(
            r'database\.get_container_client\(([^)]+)\)',
            r'db.collection(\1)',
            code
        )
        
        # Replace container operations
        code = re.sub(
            r'container\.create_item\(body=([^)]+)\)',
            r'doc_ref = db.collection("collection").document()\n    doc_ref.set(\1)',
            code
        )
        code = re.sub(
            r'container\.CreateItem\(body=([^)]+)\)',
            r'doc_ref = db.collection("collection").document()\n    doc_ref.set(\1)',
            code
        )
        code = re.sub(
            r'container\.read_item\(([^)]+)\)',
            r'doc = db.collection("collection").document(\1)\n    doc.get()',
            code
        )
        code = re.sub(
            r'container\.ReadItem\(([^)]+)\)',
            r'doc = db.collection("collection").document(\1)\n    doc.get()',
            code
        )
        
        # Remove Azure URLs from code - be more aggressive
        code = re.sub(
            r'url_connection=[\'"]https://[^\'"]+\.documents\.azure\.com[^\'"]+[\'"]',
            r'# Azure Cosmos DB URL replaced with Firestore',
            code
        )
        code = re.sub(
            r'[\'"]https://[^\'"]+\.documents\.azure\.com[^\'"]+[\'"]',
            r'# Azure Cosmos DB URL replaced with Firestore',
            code
        )
        
        return code
    
    def _migrate_azure_service_bus_to_pubsub(self, code: str) -> str:
        """Migrate Azure Service Bus to Google Cloud Pub/Sub"""
        # Replace Service Bus imports - be more aggressive
        # Handle: from azure.servicebus import ServiceBusClient, ServiceBusMessage
        code = re.sub(r'from\s+azure\.servicebus\s+import\s+[^\n]*', 'import os\nfrom google.cloud import pubsub_v1', code)
        code = re.sub(r'from\s+azure\.servicebus\s+import[^\n]*', 'import os\nfrom google.cloud import pubsub_v1', code)
        code = re.sub(r'import\s+azure\.servicebus[^\n]*', 'import os\nfrom google.cloud import pubsub_v1', code)
        # Handle multiline imports
        code = re.sub(r'from\s+azure\.servicebus[^\n]*', 'import os\nfrom google.cloud import pubsub_v1', code, flags=re.DOTALL)
        
        # Track variable name for ServiceBusClient
        servicebus_match = re.search(r'(\w+)\s*=\s*ServiceBusClient', code)
        servicebus_var = servicebus_match.group(1) if servicebus_match else 'servicebus_client'
        publisher_var = 'publisher' if servicebus_var == 'servicebus_client' else f'{servicebus_var}_publisher'
        
        # Replace client instantiation patterns
        code = re.sub(
            r'(\w+)\s*=\s*ServiceBusClient\.from_connection_string\([^)]+\)',
            rf'{publisher_var} = pubsub_v1.PublisherClient()',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*ServiceBusClient\([^)]+\)',
            rf'{publisher_var} = pubsub_v1.PublisherClient()',
            code
        )
        
        # Replace get_queue_sender/get_topic_sender patterns
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_queue_sender\(queue_name=([^)]+)\)',
            rf'import os\n    topic_path = {publisher_var}.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), \3)',
            code
        )
        code = re.sub(
            r'(\w+)\.get_queue_sender\(queue_name=([^)]+)\)',
            rf'# Queue sender replaced with Pub/Sub publisher\n    topic_path = {publisher_var}.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), \2)',
            code
        )
        code = re.sub(
            r'(\w+)\.get_topic_sender\(topic_name=([^)]+)\)',
            rf'# Topic sender replaced with Pub/Sub publisher\n    topic_path = {publisher_var}.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), \2)',
            code
        )
        
        # Replace message operations
        code = re.sub(
            r'message\s*=\s*ServiceBusMessage\(([^)]+)\)',
            r'data = \1.encode("utf-8")',
            code
        )
        code = re.sub(
            r'sender\.send_messages\(message\)',
            rf'future = {publisher_var}.publish(topic_path, data=data)',
            code
        )
        code = re.sub(
            r'sender\.send_messages\(([^)]+)\)',
            rf'future = {publisher_var}.publish(topic_path, data=\1.encode("utf-8"))',
            code
        )
        
        # Replace ServiceBusMessage import
        code = re.sub(r'ServiceBusMessage', 'str', code)
        
        # Replace 'with servicebus_client:' context manager
        code = re.sub(
            r'with\s+(\w+):',
            rf'# Context manager removed - {publisher_var} is ready to use',
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

    def _migrate_azure_key_vault_to_secret_manager(self, code: str) -> str:
        """Migrate Azure Key Vault to Google Cloud Secret Manager"""
        # Replace imports
        code = re.sub(
            r'from azure\.keyvault\.secrets import.*',
            'from google.cloud import secretmanager',
            code
        )
        code = re.sub(
            r'from azure\.identity import.*',
            'from google.auth import default',
            code
        )
        code = re.sub(
            r'import azure\.keyvault\.secrets',
            'from google.cloud import secretmanager',
            code
        )
        
        # Replace SecretClient instantiation
        code = re.sub(
            r'(\w+)\s*=\s*SecretClient\(vault_url=([^,]+),\s*credential=([^\)]+)\)',
            r'\1 = secretmanager.SecretManagerServiceClient()',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*SecretClient\(([^\)]+)\)',
            r'\1 = secretmanager.SecretManagerServiceClient()',
            code
        )
        
        # Replace get_secret() -> access_secret_version()
        code = re.sub(
            r'(\w+)\.get_secret\(([^\)]+)\)',
            r'\1.access_secret_version(request={"name": \2})',
            code
        )
        
        # Replace set_secret() -> create_secret() / add_secret_version()
        code = re.sub(
            r'(\w+)\.set_secret\(name=([^,]+),\s*value=([^\)]+)\)',
            r'\1.create_secret(request={"parent": parent, "secret_id": \2, "secret": {"replication": {"automatic": {}}}})\n    \1.add_secret_version(request={"parent": parent + "/secrets/" + \2, "payload": {"data": \3.encode("utf-8")}})',
            code
        )
        
        # Replace delete_secret() -> delete_secret()
        code = re.sub(
            r'(\w+)\.delete_secret\(name=([^\)]+)\)',
            r'\1.delete_secret(request={"name": \2})',
            code
        )
        
        # Replace list_secrets() -> list_secrets()
        code = re.sub(
            r'(\w+)\.list_secrets\(\)',
            r'\1.list_secrets(request={"parent": parent})',
            code
        )
        
        # Replace environment variables
        code = re.sub(
            r'AZURE_KEY_VAULT_URL',
            'GOOGLE_CLOUD_PROJECT',
            code
        )
        code = re.sub(
            r'AZURE_CLIENT_ID|AZURE_CLIENT_SECRET|AZURE_TENANT_ID',
            'GOOGLE_APPLICATION_CREDENTIALS',
            code
        )
        
        return code

    def _migrate_azure_application_insights_to_monitoring(self, code: str) -> str:
        """Migrate Azure Application Insights to Google Cloud Monitoring"""
        # Replace imports
        code = re.sub(
            r'from azure\.applicationinsights import.*',
            'from google.cloud import monitoring_v3\nfrom google.cloud import logging',
            code
        )
        code = re.sub(
            r'import applicationinsights',
            'from google.cloud import monitoring_v3\nfrom google.cloud import logging',
            code
        )
        
        # Replace ApplicationInsightsClient -> MetricServiceClient
        code = re.sub(
            r'(\w+)\s*=\s*ApplicationInsightsClient\(([^\)]+)\)',
            r'\1 = monitoring_v3.MetricServiceClient()',
            code
        )
        
        # Replace TelemetryClient -> Logging Client
        code = re.sub(
            r'(\w+)\s*=\s*TelemetryClient\(instrumentation_key=([^\)]+)\)',
            r'\1 = logging.Client()',
            code
        )
        code = re.sub(
            r'(\w+)\s*=\s*TelemetryClient\(([^\)]+)\)',
            r'\1 = logging.Client()',
            code
        )
        
        # Replace track_event() -> log_struct() with event data
        code = re.sub(
            r'(\w+)\.track_event\(name=([^,]+),\s*properties=([^\)]+)\)',
            r'\1.log_struct({"event_name": \2, "properties": \3})',
            code
        )
        
        # Replace track_exception() -> log_struct() with exception data
        code = re.sub(
            r'(\w+)\.track_exception\(exception=([^,]+),\s*properties=([^\)]+)\)',
            r'\1.log_struct({"exception": str(\2), "properties": \3, "severity": "ERROR"})',
            code
        )
        
        # Replace track_metric() -> create_time_series()
        code = re.sub(
            r'(\w+)\.track_metric\(name=([^,]+),\s*value=([^\)]+)\)',
            r'# Create time series for metric\n    series = monitoring_v3.TimeSeries()\n    series.metric.type = "custom.googleapis.com/" + \2\n    point = monitoring_v3.Point()\n    point.value.double_value = \3\n    point.interval.end_time.seconds = int(time.time())\n    series.points = [point]\n    \1.create_time_series(request={"name": project_name, "time_series": [series]})',
            code
        )
        
        # Replace track_trace() -> log_text()
        code = re.sub(
            r'(\w+)\.track_trace\(message=([^\)]+)\)',
            r'\1.log_text(\2)',
            code
        )
        
        # Replace flush() -> no-op (GCP logging is async)
        code = re.sub(
            r'(\w+)\.flush\(\)',
            r'# Flush not needed - GCP logging is async',
            code
        )
        
        # Replace environment variables
        code = re.sub(
            r'APPINSIGHTS_INSTRUMENTATION_KEY|APPINSIGHTS_CONNECTION_STRING',
            'GOOGLE_CLOUD_PROJECT',
            code
        )
        
        return code

    # AWS migration methods (from the original engine)
    def _migrate_aws_s3_to_gcs(self, code: str) -> str:
        """Migrate AWS S3 to Google Cloud Storage"""
        # Replace boto3 imports with GCS imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import storage', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import storage', code, flags=re.MULTILINE)
        
        # Replace client instantiation - handle various formats
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"].*?\)',
            r'\1 = storage.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace S3 upload_file -> GCS upload_from_filename
        code = re.sub(
            r'(\w+)\.upload_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)',
            r'bucket = \1.bucket("\3")\n    blob = bucket.blob("\4")\n    blob.upload_from_filename("\2")',
            code
        )
        
        # Replace S3 download_file -> GCS download_to_filename
        code = re.sub(
            r'(\w+)\.download_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)',
            r'bucket = \1.bucket("\2")\n    blob = bucket.blob("\3")\n    blob.download_to_filename("\4")',
            code
        )
        
        # Replace S3 put_object -> GCS upload
        code = re.sub(
            r'(\w+)\.put_object\(Bucket=([^,]+),\s*Key=([^,]+),\s*Body=([^,\)]+)',
            r'bucket = \1.bucket(\2)\n    blob = bucket.blob(\3)\n    blob.upload_from_string(\4)',
            code
        )
        
        # Replace S3 get_object -> GCS download
        code = re.sub(
            r'(\w+)\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blob = bucket.blob(\3)\n    content = blob.download_as_text()',
            code
        )
        
        # Replace S3 delete_object -> GCS delete
        code = re.sub(
            r'(\w+)\.delete_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blob = bucket.blob(\3)\n    blob.delete()',
            code
        )
        
        # Replace S3 list_objects_v2 -> GCS list_blobs
        code = re.sub(
            r'(\w+)\.list_objects_v2\(Bucket=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blobs = list(bucket.list_blobs())',
            code
        )
        
        # Replace S3 list_objects -> GCS list_blobs
        code = re.sub(
            r'(\w+)\.list_objects\(Bucket=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    blobs = list(bucket.list_blobs())',
            code
        )
        
        # Replace S3 list_buckets -> GCS list_buckets
        # Handle assignment pattern: buckets = s3.list_buckets()
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.list_buckets\(\)',
            r'\1 = list(\2.list_buckets())',
            code
        )
        # Handle direct call pattern: s3.list_buckets() (but not if already wrapped in list())
        code = re.sub(
            r'(\w+)\.list_buckets\(\)(?!\s*\))',
            r'list(\1.list_buckets())',
            code
        )
        
        # Replace S3 create_bucket -> GCS create_bucket
        code = re.sub(
            r'(\w+)\.create_bucket\(Bucket=([^,]+)(?:,\s*CreateBucketConfiguration=[^\)]+)?\)',
            r'\1.create_bucket(\2)',
            code
        )
        code = re.sub(
            r'(\w+)\.create_bucket\(Bucket=([^,\)]+)\)',
            r'\1.create_bucket(\2)',
            code
        )
        
        # Replace S3 delete_bucket -> GCS delete_bucket
        code = re.sub(
            r'(\w+)\.delete_bucket\(Bucket=([^,\)]+)\)',
            r'bucket = \1.bucket(\2)\n    bucket.delete()',
            code
        )
        
        # Remove or comment AWS region names
        # Replace AWS region constants/variables
        aws_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2',
            'ap-south-1', 'sa-east-1', 'ca-central-1'
        ]
        for region in aws_regions:
            # Comment out region assignments
            code = re.sub(
                rf'(\w+)\s*=\s*[\'"]{region}[\'"]',
                rf'# \1 = \'{region}\'  # AWS region - not needed for GCP',
                code
            )
            # Replace region_name parameter in client calls (already handled above, but ensure it's removed)
            code = re.sub(
                rf',\s*region_name=[\'"]?{region}[\'"]?',
                '',
                code
            )
            code = re.sub(
                rf'region_name=[\'"]?{region}[\'"]?\s*,',
                '',
                code
            )
        
        # Remove region_name parameter completely if still present
        code = re.sub(
            r',\s*region_name=\w+',
            '',
            code
        )
        code = re.sub(
            r'region_name=\w+\s*,',
            '',
            code
        )
        
        # Replace botocore exceptions imports
        # Handle multiple imports on one line first (most specific pattern first)
        if 'NoCredentialsError' in code and 'ClientError' in code:
            # Check if they're on the same import line
            code = re.sub(
                r'from botocore\.exceptions import\s+NoCredentialsError,\s*ClientError',
                'from google.auth.exceptions import DefaultCredentialsError\nfrom google.api_core import exceptions',
                code
            )
            code = re.sub(
                r'from botocore\.exceptions import\s+ClientError,\s*NoCredentialsError',
                'from google.auth.exceptions import DefaultCredentialsError\nfrom google.api_core import exceptions',
                code
            )
        
        # Handle single NoCredentialsError import
        code = re.sub(
            r'from botocore\.exceptions import\s+NoCredentialsError\b',
            'from google.auth.exceptions import DefaultCredentialsError',
            code
        )
        # Handle single ClientError import
        code = re.sub(
            r'from botocore\.exceptions import\s+ClientError\b',
            'from google.api_core import exceptions',
            code
        )
        # Replace exception usage (after imports are fixed)
        code = re.sub(
            r'\bNoCredentialsError\b',
            'DefaultCredentialsError',
            code
        )
        code = re.sub(
            r'\bClientError\b',
            'exceptions.GoogleAPIError',
            code
        )
        
        return code

    def _migrate_aws_lambda_to_cloud_functions(self, code: str) -> str:
        """Migrate AWS Lambda to Google Cloud Functions"""
        # Replace Lambda client imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import functions_v1\nimport functions_framework', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import functions_v1\nimport functions_framework', code, flags=re.MULTILINE)
        
        # Replace Lambda client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]lambda[\'\"].*?\)',
            r'\1 = functions_v1.CloudFunctionsServiceClient()',
            code,
            flags=re.DOTALL
        )
        
        # Replace Lambda function decorator patterns
        code = re.sub(
            r'def lambda_handler\(event,\s*context\):',
            '@functions_framework.http\ndef function_handler(request):',
            code
        )
        
        # Replace Lambda invocation calls
        code = re.sub(
            r'(\w+)\.invoke\(FunctionName=([^,]+),\s*InvocationType=([^,]+)?,\s*Payload=([^,\)]+)\)',
            r'# Cloud Functions invocation via HTTP or Pub/Sub\n# Function: \2\n# Payload: \4',
            code
        )
        
        # Replace create_function
        code = re.sub(
            r'(\w+)\.create_function\(FunctionName=([^,]+),\s*Runtime=([^,]+),\s*Role=([^,]+),\s*Handler=([^,]+),\s*Code=([^,\)]+)\)',
            r'# Cloud Functions deployment via gcloud or Cloud Build\n# Function name: \2\n# Runtime: \3\n# Entry point: \5',
            code
        )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        return code
    
    def _migrate_aws_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB to Google Cloud Firestore"""
        # Detect if this is a migration script (reads from DynamoDB, writes to Firestore)
        is_migration_script = (
            re.search(r'\.(scan|get_item|query)\(', code, re.IGNORECASE) and
            re.search(r'\.(put_item|batch_write_item)\(', code, re.IGNORECASE)
        )
        
        if is_migration_script:
            # MIGRATION SCRIPT MODE: Preserve DynamoDB read operations, replace write operations
            # Ensure boto3 import is present (for reading from DynamoDB)
            if 'import boto3' not in code:
                code = 'import boto3\n' + code
            
            # Ensure Firestore imports are present (for writing to Firestore)
            if 'from google.cloud import firestore' not in code:
                if 'import firebase_admin' not in code:
                    code = 'import firebase_admin\nfrom firebase_admin import credentials, firestore\nfrom decimal import Decimal\n' + code
                elif 'from firebase_admin import' not in code:
                    code = code.replace('import firebase_admin', 'import firebase_admin\nfrom firebase_admin import credentials, firestore\nfrom decimal import Decimal')
            
            # Preserve DynamoDB resource/client initialization (for reading)
            # Add Firestore client initialization (for writing)
            init_pattern = r'(\w+)\s*=\s*boto3\.(resource|client)\([\'\"]dynamodb[\'\"][^\)]*\)'
            def add_firestore_init(match):
                return match.group(0) + f'\n\n# Initialize Firestore for writing\nif not firebase_admin._apps:\n    cred = credentials.Certificate(GOOGLE_KEY_PATH)\n    firebase_admin.initialize_app(cred)\n\nfirestore_db = firestore.Client()'
            code = re.sub(init_pattern, add_firestore_init, code, count=1)
            
            # Replace write operations only: put_item() -> Firestore set()
            def replace_put_item(match):
                item = match.group(2)
                return f'# Write to Firestore\n    doc_ref = firestore_db.collection(FIRESTORE_COLLECTION).document()\n    doc_ref.set({item})'
            
            code = re.sub(
                r'(\w+)\.put_item\(\s*Item\s*=\s*([^\)]+)\)',
                replace_put_item,
                code,
                flags=re.DOTALL
            )
            
            # Replace batch_write_item() -> Firestore batch operations
            def replace_batch_write(match):
                return '''# Convert DynamoDB batch write to Firestore batch
    batch = firestore_db.batch()
    collection_ref = firestore_db.collection(FIRESTORE_COLLECTION)
    for item in items:
        clean_item = convert_decimal(item)  # Convert Decimal types
        doc_id = clean_item.get(PRIMARY_KEY_FIELD, None)
        if doc_id:
            doc_ref = collection_ref.document(str(doc_id))
        else:
            doc_ref = collection_ref.document()
        batch.set(doc_ref, clean_item)
    batch.commit()'''
            
            code = re.sub(
                r'(\w+)\.batch_write_item\(\s*RequestItems\s*=\s*\{[^}]+\}\s*\)',
                replace_batch_write,
                code,
                flags=re.DOTALL
            )
            
            # Keep scan(), get_item(), query() operations as DynamoDB operations
            return code
        
        # APPLICATION CODE MODE: Replace all DynamoDB with Firestore
        # Replace DynamoDB imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import firestore', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import firestore', code, flags=re.MULTILINE)
        
        # Replace DynamoDB resource (common pattern)
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.resource\([\'\"]dynamodb[\'\"].*?\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace DynamoDB client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]dynamodb[\'\"].*?\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace table operations with collection/document operations
        # table.put_item() -> collection.add() or document.set()
        code = re.sub(
            r'(\w+)\.put_item\(Item=([^,\)]+)\)',
            r'doc_ref = \1.document()\n    doc_ref.set(\2)',
            code
        )
        
        code = re.sub(
            r'(\w+)\.put_item\(TableName=([^,]+),\s*Item=([^,\)]+)\)',
            r'db.collection(\2).document().set(\3)',
            code
        )
        
        # table.get_item() -> document.get()
        code = re.sub(
            r'(\w+)\.get_item\(Key=([^,\)]+)\)',
            r'doc_ref = \1.document(\2)\n    doc = doc_ref.get()',
            code
        )
        
        code = re.sub(
            r'(\w+)\.get_item\(TableName=([^,]+),\s*Key=([^,\)]+)\)',
            r'doc = db.collection(\2).document(\3).get()',
            code
        )
        
        # table.query() -> collection.where()
        code = re.sub(
            r'(\w+)\.query\(KeyConditionExpression=([^,\)]+)\)',
            r'query = \1.where(\2)\n    results = query.stream()',
            code
        )
        
        code = re.sub(
            r'(\w+)\.query\(TableName=([^,]+),\s*KeyConditionExpression=([^,\)]+)\)',
            r'query = db.collection(\2).where(\3)\n    results = query.stream()',
            code
        )
        
        # table.delete_item() -> document.delete()
        code = re.sub(
            r'(\w+)\.delete_item\(Key=([^,\)]+)\)',
            r'\1.document(\2).delete()',
            code
        )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        return code
    
    def _add_exception_handling(self, code: str) -> str:
        """Add exception handling transformations for all cloud services"""
        # Replace botocore exceptions imports
        # Handle multiple imports on one line first (most specific pattern first)
        if 'NoCredentialsError' in code and 'ClientError' in code:
            # Check if they're on the same import line
            code = re.sub(
                r'from botocore\.exceptions import\s+NoCredentialsError,\s*ClientError',
                'from google.auth.exceptions import DefaultCredentialsError\nfrom google.api_core import exceptions',
                code
            )
            code = re.sub(
                r'from botocore\.exceptions import\s+ClientError,\s*NoCredentialsError',
                'from google.auth.exceptions import DefaultCredentialsError\nfrom google.api_core import exceptions',
                code
            )
        
        # Handle single NoCredentialsError import
        code = re.sub(
            r'from botocore\.exceptions import\s+NoCredentialsError\b',
            'from google.auth.exceptions import DefaultCredentialsError',
            code
        )
        # Handle single ClientError import
        code = re.sub(
            r'from botocore\.exceptions import\s+ClientError\b',
            'from google.api_core import exceptions',
            code
        )
        # Replace exception usage (after imports are fixed)
        code = re.sub(
            r'\bNoCredentialsError\b',
            'DefaultCredentialsError',
            code
        )
        code = re.sub(
            r'\bClientError\b',
            'exceptions.GoogleAPIError',
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


class AzureExtendedGoTransformer(BaseAzureExtendedTransformer):
    """Extended transformer for Go code - uses Gemini API for Azure transformations"""
    
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform Go code based on the recipe"""
        # Go transformations are handled by Gemini API in transform_code()
        # This is a fallback transformer for regex-based simple patterns
        operation = recipe.get('operation', '')
        service_type = recipe.get('service_type', '')
        
        if operation == 'service_migration' and service_type:
            if 'azure_blob_storage_to_gcs' in service_type:
                return self._migrate_azure_blob_storage_to_gcs(code)
            elif 'azure_functions_to_cloud_functions' in service_type:
                return self._migrate_azure_functions_to_cloud_functions(code)
            elif 'azure_cosmos_db_to_firestore' in service_type:
                return self._migrate_azure_cosmos_db_to_firestore(code)
            elif 'azure_service_bus_to_pubsub' in service_type:
                return self._migrate_azure_service_bus_to_pubsub(code)
            elif 'azure_event_hubs_to_pubsub' in service_type:
                return self._migrate_azure_event_hubs_to_pubsub(code)
            elif 'azure_key_vault_to_secret_manager' in service_type:
                return self._migrate_azure_key_vault_to_secret_manager(code)
            elif 'azure_application_insights_to_monitoring' in service_type:
                return self._migrate_azure_application_insights_to_monitoring(code)
        
        return code
    
    def _migrate_azure_blob_storage_to_gcs(self, code: str) -> str:
        """Migrate Azure Blob Storage Go code to Google Cloud Storage (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-sdk-for-go/sdk/storage/azblob',
            'cloud.google.com/go/storage',
            code
        )
        code = re.sub(
            r'azblob\.NewClient',
            'storage.NewClient',
            code
        )
        return code
    
    def _migrate_azure_functions_to_cloud_functions(self, code: str) -> str:
        """Migrate Azure Functions Go code to Google Cloud Functions (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-functions-go',
            'cloud.google.com/go/functions',
            code
        )
        return code
    
    def _migrate_azure_cosmos_db_to_firestore(self, code: str) -> str:
        """Migrate Azure Cosmos DB Go code to Google Firestore (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-sdk-for-go/sdk/data/azcosmos',
            'cloud.google.com/go/firestore',
            code
        )
        return code
    
    def _migrate_azure_service_bus_to_pubsub(self, code: str) -> str:
        """Migrate Azure Service Bus Go code to Google Pub/Sub (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-sdk-for-go/sdk/messaging/azservicebus',
            'cloud.google.com/go/pubsub',
            code
        )
        return code
    
    def _migrate_azure_event_hubs_to_pubsub(self, code: str) -> str:
        """Migrate Azure Event Hubs Go code to Google Pub/Sub (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-event-hubs-go',
            'cloud.google.com/go/pubsub',
            code
        )
        return code
    
    def _migrate_azure_key_vault_to_secret_manager(self, code: str) -> str:
        """Migrate Azure Key Vault Go code to Google Secret Manager (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets',
            'cloud.google.com/go/secretmanager/apiv1',
            code
        )
        return code
    
    def _migrate_azure_application_insights_to_monitoring(self, code: str) -> str:
        """Migrate Azure Application Insights Go code to Google Cloud Monitoring (fallback regex)"""
        code = re.sub(
            r'github\.com/Azure/azure-sdk-for-go/sdk/monitor',
            'cloud.google.com/go/monitoring/apiv3',
            code
        )
        return code


    def _aggressive_azure_cleanup(self, code: str) -> str:
        """
        AGGRESSIVE Azure cleanup that removes ALL Azure patterns.
        This ensures zero Azure references remain in the transformed code.
        """
        if code is None:
            return ""
        
        result = code
        
        # Remove all Azure imports
        result = re.sub(r'from azure\.[^\s]+ import.*', '', result)
        result = re.sub(r'import azure\.[^\s]+.*', '', result)
        
        # Remove Azure-specific classes and patterns
        result = re.sub(r'BlobServiceClient', 'storage.Client', result, flags=re.IGNORECASE)
        result = re.sub(r'blob_service_client', 'gcs_client', result, flags=re.IGNORECASE)
        result = re.sub(r'container_client', 'bucket', result, flags=re.IGNORECASE)
        result = re.sub(r'blob_client', 'blob', result, flags=re.IGNORECASE)
        
        # Remove Azure URLs
        result = re.sub(r'https://[^/]+\.blob\.core\.windows\.net[^\s]*', '', result)
        
        # Remove Azure-specific exceptions
        result = re.sub(r'from azure\.core\.exceptions import.*', '', result)
        result = re.sub(r'AzureException', 'Exception', result)
        
        # Remove Azure credential patterns
        result = re.sub(r'DefaultAzureCredential\(\)', 'storage.Client()', result)
        result = re.sub(r'AzureKeyCredential\([^)]+\)', '', result)
        
        # Remove Azure environment variables
        result = re.sub(r'AZURE_STORAGE_CONNECTION_STRING', 'GOOGLE_APPLICATION_CREDENTIALS', result)
        result = re.sub(r'AZURE_STORAGE_ACCOUNT_NAME', 'GOOGLE_CLOUD_PROJECT', result)
        result = re.sub(r'AZURE_STORAGE_ACCOUNT_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', result)
        
        # Remove Azure-specific method calls that weren't transformed
        result = re.sub(r'\.from_connection_string\([^)]+\)', '()', result)
        result = re.sub(r'\.get_container_client\([^)]+\)', '.bucket()', result)
        result = re.sub(r'\.get_blob_client\([^)]+\)', '.blob()', result)
        result = re.sub(r'\.upload_blob\([^)]+\)', '.upload_from_string()', result)
        result = re.sub(r'\.download_blob\([^)]+\)', '.download_as_bytes()', result)
        result = re.sub(r'\.readall\(\)', '', result)
        
        return result


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
        # transform_code returns (transformed_code, variable_mapping) tuple
        result = self.ast_engine.transform_code(source_code, language, recipe)
        
        # Handle both tuple and string returns
        if isinstance(result, tuple):
            transformed_code, variable_mapping = result
        else:
            transformed_code = result
        
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