"""
Validate GCP Code Use Case

Architectural Intent:
- Validates that refactored code is correct for Google Cloud Platform
- Checks for AWS/Azure patterns, syntax errors, and GCP API correctness
- Provides detailed validation results with progress tracking
"""

import ast
import re
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of code validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    aws_patterns_found: List[str]
    azure_patterns_found: List[str]
    syntax_valid: bool
    gcp_api_correct: bool
    validation_details: Dict[str, Any]


class ValidateGCPCodeUseCase:
    """Use case for validating Google Cloud Platform code correctness"""
    
    # AWS patterns to detect
    AWS_PATTERNS = [
        'boto3', 'botocore', 's3.buckets', 's3.meta.client', 
        's3.Bucket', 's3.create_bucket', 's3.upload_file',
        's3.download_file', 's3.list_objects', 'ResponseMetadata',
        'LocationConstraint', 'ACL', 'CreateBucketConfiguration',
        's3_client', 's3_bucket', 's3_key', 's3_object',
        'Bucket=', 'Key=', 'QueueUrl=', 'TopicArn=',
        'FunctionName=', 'InvocationType=', 'Payload=', 'Region=',
        'aws_access_key', 'aws_secret', 'AWS_ACCESS_KEY', 'AWS_SECRET',
        'amazonaws.com', 's3://', 'S3Manager', 'S3Client',
        'dynamodb_client', 'sqs_client', 'sns_client', 'lambda_handler',
        'DYNAMODB_TABLE_NAME', 'SQS_DLQ_URL', 'SNS_TOPIC_ARN',
        "event['Records']", 'event["Records"]', "record_event['s3']",
        'record_event["s3"]', 'get_object', 'batch_write_item',
        'send_message', 'QueueUrl', 'TopicArn', 'RequestItems',
        'PutRequest', 'Item=', 'MessageBody=', 'Message=',
        'boto3.client', 'boto3.resource', 'boto3.Session',
        # ECS/Fargate patterns
        'fargate', 'Fargate', 'FARGATE', 'ecs', 'ECS',
        'run_task', 'register_task_definition', 'start_task',
        'list_tasks', 'describe_tasks', 'stop_task',
        'taskDefinition', 'taskDefinitionArn', 'cluster',
        'containerDefinitions', 'family', 'taskArn',
        # RDS patterns
        'rds_client', 'rds.Client', 'boto3.client(\'rds\'',
        'create_db_instance', 'delete_db_instance', 'describe_db_instances',
        'modify_db_instance', 'DBInstanceIdentifier', 'DBInstanceClass',
        'Engine', 'MasterUsername', 'MasterUserPassword', 'AllocatedStorage',
        'RDS_ENDPOINT', 'RDS_HOST', 'RDS_DB_NAME', 'RDS_USERNAME', 'RDS_PASSWORD'
    ]
    
    # Azure patterns to detect
    AZURE_PATTERNS = [
        'azure.storage', 'azure.functions', 'azure.cosmos', 
        'azure.servicebus', 'azure.eventhub', 'BlobServiceClient',
        'CosmosClient', 'ServiceBusClient', 'EventHubProducerClient',
        'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_LOCATION',
        'AZURE_STORAGE_CONTAINER', 'azure.core', 'azure.identity',
        'BlobClient', 'ContainerClient', 'QueueClient', 'TopicClient'
    ]
    
    # GCP patterns that should be present
    GCP_PATTERNS = [
        'google.cloud', 'storage.Client', 'firestore.Client',
        'pubsub_v1', 'cloudfunctions', 'cloudsql', 'gke',
        'GCP_PROJECT_ID', 'GCP_REGION', 'GCS_BUCKET_NAME',
        'gs://', 'google.api_core', 'google.auth'
    ]
    
    # AWS method patterns (regex)
    AWS_METHOD_PATTERNS = [
        r'\bboto3\s*\.\s*(client|resource)\s*\(',
        r'\bs3\s*\.\s*\w+',
        r'\w+\s*\.\s*create_bucket\s*\(',
        r'\w+\s*\.\s*upload_file\s*\(',
        r'\w+\s*\.\s*download_file\s*\(',
        r'\w+\s*\.\s*list_objects',
        r'\w+\s*\.\s*delete_object\s*\(',
        r'\w+\s*\.\s*put_object\s*\(',
        r'\w+\s*\.\s*get_object\s*\(',
        r'\w+\s*\.\s*batch_write_item\s*\(',
        r'\w+\s*\.\s*send_message\s*\(',
        r'\w+\s*\.\s*publish\s*\([^)]*TopicArn',
        r'lambda_handler\s*\(',
        r'event\s*\[\s*[\'"]Records[\'"]\s*\]',
        r'record_event\s*\[\s*[\'"]s3[\'"]\s*\]',
        # ECS/Fargate patterns
        r'\w+\s*\.\s*run_task\s*\(',
        r'\w+\s*\.\s*register_task_definition\s*\(',
        r'\w+\s*\.\s*start_task\s*\(',
        r'\w+\s*\.\s*list_tasks\s*\(',
        r'\w+\s*\.\s*describe_tasks\s*\(',
        r'\w+\s*\.\s*stop_task\s*\(',
        r'\bfargate\b',
        r'\bFargate\b',
        r'\bFARGATE\b',
        r'\becs\s*\.\s*client',
        # RDS patterns
        r'\brds\s*\.\s*client',
        r'\brds_client\b',
        r'\w+\s*\.\s*create_db_instance\s*\(',
        r'\w+\s*\.\s*delete_db_instance\s*\(',
        r'\w+\s*\.\s*describe_db_instances\s*\(',
        r'\w+\s*\.\s*modify_db_instance\s*\(',
        r'\bDBInstanceIdentifier\b',
        r'\bDBInstanceClass\b',
        r'\bRDS_ENDPOINT\b',
        r'\bRDS_HOST\b',
    ]
    
    def __init__(self, llm_provider: Optional[Any] = None):
        """Initialize validation use case
        
        Args:
            llm_provider: Optional LLM provider for advanced validation
        """
        self.llm_provider = llm_provider
    
    def validate(
        self, 
        code: str, 
        language: str = 'python',  # Supports: python, java, csharp, c#
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> ValidationResult:
        """
        Validate code for Google Cloud Platform correctness
        
        Args:
            code: Code to validate
            language: Programming language ('python', 'java', 'csharp', or 'c#')
            progress_callback: Optional callback for progress updates (message, percentage)
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        aws_patterns_found = []
        azure_patterns_found = []
        
        if progress_callback:
            progress_callback("Starting validation...", 0.0)
        
        # Step 1: Syntax validation (20%)
        syntax_valid = self._validate_syntax(code, language)
        if progress_callback:
            progress_callback("Syntax validation complete", 20.0)
        
        if not syntax_valid:
            errors.append("Code contains syntax errors")
        
        # Step 2: Check for AWS patterns (40%)
        aws_patterns_found = self._detect_aws_patterns(code, language)
        if progress_callback:
            progress_callback(f"Found {len(aws_patterns_found)} AWS patterns", 40.0)
        
        if aws_patterns_found:
            errors.append(f"Found {len(aws_patterns_found)} AWS patterns in code")
            warnings.append("Code may not be fully migrated to GCP")
        
        # Step 3: Check for Azure patterns (60%)
        # Only check Azure patterns if no AWS patterns were found
        # This prevents false positives when validating AWS service migrations
        azure_patterns_found = []
        if not aws_patterns_found:
            azure_patterns_found = self._detect_azure_patterns(code)
            if progress_callback:
                progress_callback(f"Found {len(azure_patterns_found)} Azure patterns", 60.0)
            
            if azure_patterns_found:
                errors.append(f"Found {len(azure_patterns_found)} Azure patterns in code")
                warnings.append("Code may not be fully migrated to GCP")
        else:
            # Skip Azure check if AWS patterns found (likely AWS migration)
            if progress_callback:
                progress_callback("Skipping Azure pattern check (AWS patterns detected)", 60.0)
        
        # Step 4: Check GCP API correctness (80%)
        gcp_api_correct = self._validate_gcp_apis(code, language)
        if progress_callback:
            progress_callback("GCP API validation complete", 80.0)
        
        # Only warn about GCP API if:
        # 1. We found AWS/Azure patterns (meaning migration was attempted)
        # 2. AND GCP APIs are not detected
        # This prevents false positives for code that doesn't use cloud services
        if not gcp_api_correct and (aws_patterns_found or azure_patterns_found):
            # Check if code actually uses cloud services (not just simple Python code)
            has_cloud_operations = any(pattern in code.lower() for pattern in [
                'client', 'bucket', 'blob', 'collection', 'document', 'topic', 
                'subscription', 'function', 'service', 'instance', 'cluster'
            ])
            if has_cloud_operations:
                warnings.append("GCP API usage may be incorrect or incomplete - verify GCP SDK imports and client initialization")
        
        # Step 5: Advanced LLM validation if available (100%)
        if self.llm_provider and (aws_patterns_found or azure_patterns_found):
            llm_validation = self._llm_validate(code, language)
            if progress_callback:
                progress_callback("Advanced validation complete", 100.0)
            
            if llm_validation.get('has_issues'):
                errors.extend(llm_validation.get('errors', []))
                warnings.extend(llm_validation.get('warnings', []))
        elif progress_callback:
            progress_callback("Validation complete", 100.0)
        
        is_valid = len(errors) == 0 and syntax_valid
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            aws_patterns_found=aws_patterns_found,
            azure_patterns_found=azure_patterns_found,
            syntax_valid=syntax_valid,
            gcp_api_correct=gcp_api_correct,
            validation_details={
                'total_patterns_found': len(aws_patterns_found) + len(azure_patterns_found),
                'has_aws_patterns': len(aws_patterns_found) > 0,
                'has_azure_patterns': len(azure_patterns_found) > 0,
                'language': language
            }
        )
    
    def _validate_syntax(self, code: str, language: str) -> bool:
        """Validate code syntax"""
        if not code or not code.strip():
            # Empty code is syntactically valid (though may not be useful)
            return True
            
        try:
            if language == 'python':
                # Try to parse the code
                try:
                    ast.parse(code)
                    return True
                except SyntaxError as e:
                    logger.error(f"Syntax error: {e} at line {e.lineno}")
                    return False
                except Exception as e:
                    logger.error(f"AST parsing error: {e}")
                    return False
            elif language == 'java':
                # Basic Java syntax check - could be enhanced
                # For now, just check for basic structure
                # Check for balanced braces and basic structure
                if '{' not in code or '}' not in code:
                    return False
            elif language in ['csharp', 'c#']:
                # Basic C# syntax check
                # Check for balanced braces and basic structure
                if '{' not in code or '}' not in code:
                    return False
                # C# should have using statements or namespace
                if 'using' not in code and 'namespace' not in code:
                    return False
                # Check for balanced braces
                open_braces = code.count('{')
                close_braces = code.count('}')
                if open_braces != close_braces:
                    return False
                return True
            return True
        except Exception as e:
            logger.error(f"Syntax validation error: {e}")
            return False
    
    def _detect_aws_patterns(self, code: str, language: str = 'python') -> List[str]:
        """Detect AWS patterns in code"""
        found_patterns = []
        code_lower = code.lower()
        
        # Use language-specific patterns if C#
        patterns_to_check = self.AWS_PATTERNS
        if language in ['csharp', 'c#']:
            # Add C#-specific AWS patterns
            csharp_patterns = [
                'Amazon.',
                'AWSSDK.',
                'AmazonS3',
                'AmazonDynamoDB',
                'AmazonSQS',
                'AmazonSNS',
                'AmazonLambda',
                'ILambdaContext',
                'APIGatewayProxy',
                'IAmazon',
                'S3Client',
                'DynamoDBClient',
                'SQSClient',
                'SNSClient',
            ]
            patterns_to_check = list(self.AWS_PATTERNS) + csharp_patterns
        
        # Check literal patterns - be more precise to avoid false positives
        for pattern in patterns_to_check:
            pattern_lower = pattern.lower()
            if pattern_lower in code_lower:
                # Skip common false positives that might appear in GCP code
                # These patterns are too generic and might match legitimate GCP code
                false_positives = [
                    'region=',     # Too generic - GCP uses regions too
                    'functionname=',  # Too generic
                    'engine',      # Too generic - Cloud SQL uses engine too
                ]
                
                # Only add if not a false positive
                if pattern_lower not in false_positives:
                    found_patterns.append(pattern)
        
        # Check regex patterns - these are more precise
        for pattern in self.AWS_METHOD_PATTERNS:
            # Skip patterns that might match comments or false positives
            if language == 'java' and pattern == r'\bs3\s*\.\s*\w+':
                # For Java, only match if it's an actual method call, not in comments
                # Check if it's in a comment line
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    # Skip comment lines
                    if stripped.startswith('//') or stripped.startswith('*') or '/*' in stripped:
                        continue
                    matches = re.findall(pattern, line, re.IGNORECASE)
                    if matches:
                        pattern_name = self._extract_pattern_name(pattern, matches[0] if matches else None)
                        if pattern_name and pattern_name not in found_patterns:
                            found_patterns.append(pattern_name)
                        break
            else:
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    # Extract meaningful pattern name from regex
                    pattern_name = self._extract_pattern_name(pattern, matches[0] if matches else None)
                    if pattern_name and pattern_name not in found_patterns:
                        found_patterns.append(pattern_name)
        
        return list(set(found_patterns))  # Remove duplicates
    
    def _extract_pattern_name(self, regex_pattern: str, match: str = None) -> str:
        """Extract a human-readable pattern name from regex"""
        # Map regex patterns to readable names
        pattern_map = {
            r'\bboto3\s*\.\s*(client|resource)\s*\(': 'boto3.client() or boto3.resource()',
            r'\bs3\s*\.\s*\w+': 'S3 operation',  # Only match actual method calls, not comments
            r'\w+\s*\.\s*create_bucket\s*\(': 'create_bucket()',
            r'\w+\s*\.\s*upload_file\s*\(': 'upload_file()',
            r'\w+\s*\.\s*download_file\s*\(': 'download_file()',
            r'\w+\s*\.\s*list_objects': 'list_objects()',
            r'\w+\s*\.\s*delete_object\s*\(': 'delete_object()',
            r'\w+\s*\.\s*put_object\s*\(': 'put_object()',
            r'\w+\s*\.\s*get_object\s*\(': 'get_object()',
            r'\w+\s*\.\s*batch_write_item\s*\(': 'batch_write_item()',
            r'\w+\s*\.\s*send_message\s*\(': 'send_message()',
            r'\w+\s*\.\s*publish\s*\([^)]*TopicArn': 'publish() with TopicArn',
            r'lambda_handler\s*\(': 'lambda_handler()',
            r'event\s*\[\s*[\'"]Records[\'"]\s*\]': "event['Records']",
            r'record_event\s*\[\s*[\'"]s3[\'"]\s*\]': "record_event['s3']",
            r'\w+\s*\.\s*run_task\s*\(': 'run_task()',
            r'\w+\s*\.\s*register_task_definition\s*\(': 'register_task_definition()',
            r'\w+\s*\.\s*start_task\s*\(': 'start_task()',
            r'\w+\s*\.\s*list_tasks\s*\(': 'list_tasks()',
            r'\w+\s*\.\s*describe_tasks\s*\(': 'describe_tasks()',
            r'\w+\s*\.\s*stop_task\s*\(': 'stop_task()',
            r'\bfargate\b': 'Fargate',
            r'\bFargate\b': 'Fargate',
            r'\bFARGATE\b': 'Fargate',
            r'\becs\s*\.\s*client': 'ECS client',
            r'\brds\s*\.\s*client': 'RDS client',
            r'\brds_client\b': 'rds_client',
            r'\w+\s*\.\s*create_db_instance\s*\(': 'create_db_instance()',
            r'\w+\s*\.\s*delete_db_instance\s*\(': 'delete_db_instance()',
            r'\w+\s*\.\s*describe_db_instances\s*\(': 'describe_db_instances()',
            r'\w+\s*\.\s*modify_db_instance\s*\(': 'modify_db_instance()',
            r'\bDBInstanceIdentifier\b': 'DBInstanceIdentifier',
            r'\bDBInstanceClass\b': 'DBInstanceClass',
            r'\bRDS_ENDPOINT\b': 'RDS_ENDPOINT',
            r'\bRDS_HOST\b': 'RDS_HOST',
        }
        
        # Return mapped name or simplified regex pattern
        if regex_pattern in pattern_map:
            return pattern_map[regex_pattern]
        
        # Fallback: extract key part of pattern
        if match:
            return str(match)
        
        # Last resort: return simplified pattern
        return regex_pattern.replace(r'\b', '').replace(r'\s*', ' ').replace(r'\w+', 'method').replace('\\', '')[:50]
    
    def _detect_azure_patterns(self, code: str) -> List[str]:
        """Detect Azure patterns in code"""
        found_patterns = []
        code_lower = code.lower()
        
        for pattern in self.AZURE_PATTERNS:
            if pattern.lower() in code_lower or pattern in code:
                found_patterns.append(pattern)
        
        return list(set(found_patterns))  # Remove duplicates
    
    def _validate_gcp_apis(self, code: str, language: str) -> bool:
        """Validate that GCP APIs are used correctly"""
        if language in ['csharp', 'c#']:
            # Check for GCP C# imports
            has_gcp_imports = any(pattern in code for pattern in [
                'using Google.Cloud',
                'Google.Cloud.Storage',
                'Google.Cloud.Firestore',
                'Google.Cloud.PubSub',
                'Google.Cloud.Functions',
                'Google.Cloud.Bigtable',
                'Google.Cloud.Sql',
                'Google.Cloud.Compute',
                'Google.Cloud.Monitoring',
                'Google.Cloud.Container',
                'Google.Cloud.Run',
                'Google.Api.Gax',
            ])
            
            # Check for proper GCP client initialization
            has_gcp_clients = any(pattern in code for pattern in [
                'StorageClient',
                'FirestoreDb',
                'PublisherClient',
                'SubscriberClient',
                'FunctionsFramework',
            ])
            
            return has_gcp_imports or has_gcp_clients
        elif language == 'python':
            # Check for GCP imports - be flexible with import styles
            has_gcp_imports = any(pattern in code for pattern in [
                'from google.cloud', 'import google.cloud',
                'google.cloud.storage', 'google.cloud.firestore',
                'google.cloud.pubsub', 'google.cloud.functions',
                'google.cloud.bigtable', 'google.cloud.sql',
                'google.cloud.compute', 'google.cloud.monitoring',
                'google.cloud.endpoints', 'google.cloud.apigee',
                'google.cloud.container', 'google.cloud.run',
                'google.cloud.run_v2', 'from google.cloud.run_v2',
                'google.cloud.memorystore', 'google.api_core',
                'google.auth', 'google.generativeai'
            ])
            
            # Check for proper GCP client initialization
            has_gcp_clients = any(pattern in code for pattern in [
                'storage.Client()', 'firestore.Client()',
                'pubsub_v1.PublisherClient()', 'pubsub_v1.SubscriberClient()',
                'bigtable.Client()', 'sql.Client()',
                'compute.Client()', 'monitoring.Client()',
                'container_v1.ClusterManagerClient()',
                'run_v2.ServicesClient()', 'run_v2.JobsClient()',
                'run_v2.ExecutionsClient()', 'run_v2.RevisionsClient()',
                'ServicesClient()', 'JobsClient()',  # Cloud Run clients without full path
                'run_v2',  # Cloud Run v2 API usage
                'Client()', '.Client()'  # Generic client pattern
            ])
            
            # Also check for GCP environment variables
            has_gcp_env_vars = any(pattern in code for pattern in [
                'GCP_PROJECT_ID', 'GCP_REGION', 'GCS_BUCKET_NAME',
                'GCP_CLOUD_FUNCTION_NAME', 'GCP_CLOUD_RUN_SERVICE_NAME',
                'GCP_CLOUD_RUN_IMAGE', 'GCP_CLOUD_RUN_JOB_NAME',
                'GCP_FIRESTORE_COLLECTION_NAME', 'GCP_PUBSUB_TOPIC_ID',
                'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_PROJECT'
            ])
            
            # Check for GCP-specific method calls (even without explicit imports)
            has_gcp_methods = any(pattern in code.lower() for pattern in [
                '.bucket(', '.blob(', '.download_as_text', '.upload_from',
                '.collection(', '.document(', '.download', '.upload',
                '.publish(', '.subscribe(', 'gs://',
                # Cloud Run specific patterns
                '.create_service(', '.get_service(', '.list_services(',
                '.create_job(', '.run_job(', '.get_job(', '.list_jobs(',
                'run_v2', 'cloud.run', 'cloud_run',
                'run_v2.service', 'run_v2.job', 'run_v2.container',
                'createservicerequest', 'createjobrequest', 'runjobrequest',
                'executiontemplate', 'revisiontemplate'
            ])
            
            # If code has no cloud operations at all, consider it valid
            # (simple Python code without cloud services)
            has_cloud_indicators = any(pattern in code.lower() for pattern in [
                'client', 'bucket', 'blob', 'storage', 'database', 'queue',
                'topic', 'function', 'service', 'instance'
            ])
            
            # Return True if:
            # 1. Has GCP imports/clients/env vars (explicit GCP usage), OR
            # 2. Has GCP methods (implicit GCP usage), OR
            # 3. No cloud indicators at all (simple code, not cloud-related)
            return has_gcp_imports or has_gcp_clients or has_gcp_env_vars or has_gcp_methods or not has_cloud_indicators
        
        return True  # For other languages, assume valid if no errors
    
    def _llm_validate(self, code: str, language: str) -> Dict[str, Any]:
        """Use LLM for advanced validation"""
        if not self.llm_provider:
            return {'has_issues': False}
        
        try:
            import google.generativeai as genai
            from config import Config
            
            if not Config.GEMINI_API_KEY:
                return {'has_issues': False}
            
            genai.configure(api_key=Config.GEMINI_API_KEY)
            
            # Use fastest model for validation
            try:
                model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception:
                try:
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
                except Exception:
                    return {'has_issues': False}
            
            prompt = f"""Analyze this {language} code that was refactored from AWS/Azure to Google Cloud Platform.

Code:
```{language}
{code}
```

Check for:
1. Any remaining AWS or Azure patterns
2. Incorrect GCP API usage
3. Missing GCP imports
4. Syntax errors

Respond with JSON:
{{
    "has_issues": true/false,
    "errors": ["error1", "error2"],
    "warnings": ["warning1", "warning2"]
}}"""
            
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            import json
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            
            return {'has_issues': False}
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            return {'has_issues': False}
