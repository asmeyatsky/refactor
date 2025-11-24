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
        'Bucket=', 'Key=', 'QueueUrl=', 'TopicArn=', 'TableName=',
        'FunctionName=', 'InvocationType=', 'Payload=', 'Region=',
        'aws_access_key', 'aws_secret', 'AWS_ACCESS_KEY', 'AWS_SECRET',
        'amazonaws.com', '.s3.', 's3://', 'S3Manager', 'S3Client',
        'dynamodb_client', 'sqs_client', 'sns_client', 'lambda_handler',
        'DYNAMODB_TABLE_NAME', 'SQS_DLQ_URL', 'SNS_TOPIC_ARN',
        "event['Records']", 'event["Records"]', "record_event['s3']",
        'record_event["s3"]', 'get_object', 'batch_write_item',
        'send_message', 'QueueUrl', 'TopicArn', 'RequestItems',
        'PutRequest', 'Item=', 'MessageBody=', 'Message=',
        'boto3.client', 'boto3.resource', 'boto3.Session'
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
        language: str = 'python',
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> ValidationResult:
        """
        Validate code for Google Cloud Platform correctness
        
        Args:
            code: Code to validate
            language: Programming language ('python' or 'java')
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
        aws_patterns_found = self._detect_aws_patterns(code)
        if progress_callback:
            progress_callback(f"Found {len(aws_patterns_found)} AWS patterns", 40.0)
        
        if aws_patterns_found:
            errors.append(f"Found {len(aws_patterns_found)} AWS patterns in code")
            warnings.append("Code may not be fully migrated to GCP")
        
        # Step 3: Check for Azure patterns (60%)
        azure_patterns_found = self._detect_azure_patterns(code)
        if progress_callback:
            progress_callback(f"Found {len(azure_patterns_found)} Azure patterns", 60.0)
        
        if azure_patterns_found:
            errors.append(f"Found {len(azure_patterns_found)} Azure patterns in code")
            warnings.append("Code may not be fully migrated to GCP")
        
        # Step 4: Check GCP API correctness (80%)
        gcp_api_correct = self._validate_gcp_apis(code, language)
        if progress_callback:
            progress_callback("GCP API validation complete", 80.0)
        
        if not gcp_api_correct:
            warnings.append("GCP API usage may be incorrect or incomplete")
        
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
        try:
            if language == 'python':
                ast.parse(code)
                return True
            elif language == 'java':
                # Basic Java syntax check - could be enhanced
                # For now, just check for basic structure
                return '{' in code and '}' in code
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error: {e}")
            return False
        except Exception as e:
            logger.error(f"Syntax validation error: {e}")
            return False
    
    def _detect_aws_patterns(self, code: str) -> List[str]:
        """Detect AWS patterns in code"""
        found_patterns = []
        code_lower = code.lower()
        
        # Check literal patterns
        for pattern in self.AWS_PATTERNS:
            if pattern.lower() in code_lower or pattern in code:
                found_patterns.append(pattern)
        
        # Check regex patterns
        for pattern in self.AWS_METHOD_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                found_patterns.extend([f"Pattern: {pattern}" for _ in matches])
        
        return list(set(found_patterns))  # Remove duplicates
    
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
        if language == 'python':
            # Check for GCP imports
            has_gcp_imports = any(pattern in code for pattern in [
                'from google.cloud', 'import google.cloud',
                'google.cloud.storage', 'google.cloud.firestore',
                'google.cloud.pubsub', 'google.cloud.functions'
            ])
            
            # Check for proper GCP client initialization
            has_gcp_clients = any(pattern in code for pattern in [
                'storage.Client()', 'firestore.Client()',
                'pubsub_v1.PublisherClient()', 'pubsub_v1.SubscriberClient()'
            ])
            
            return has_gcp_imports or has_gcp_clients
        
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
