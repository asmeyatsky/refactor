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
    
    def transform_code(self, code: str, language: str, transformation_recipe: Dict[str, Any]) -> tuple[str, dict]:
        """
        Transform code based on the transformation recipe.
        NEW APPROACH: Use Gemini FIRST for transformation, regex only for simple patterns.
        This is more reliable than regex-based transformation.
        
        Returns:
            tuple: (transformed_code, variable_mapping) where variable_mapping is a dict
                   mapping old variable names to new variable names
        """
        if language not in self.transformers:
            raise ValueError(f"Unsupported language: {language}")

        # NEW APPROACH: Use Gemini as PRIMARY transformer
        if language == 'python':
            transformed_code = self._transform_with_gemini_primary(code, transformation_recipe)
            
            # Only use regex for simple, unambiguous patterns (imports)
            transformed_code = self._apply_simple_regex_fixes(transformed_code)
            
            # Validate output - reject if still has AWS patterns or syntax errors
            max_retries = 2
            retry_count = 0
            while (self._has_aws_patterns(transformed_code) or not self._is_valid_syntax(transformed_code)) and retry_count < max_retries:
                retry_count += 1
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Output still contains AWS patterns or syntax errors, retrying (attempt {retry_count}/{max_retries})")
                transformed_code = self._transform_with_gemini_primary(code, transformation_recipe, retry=True)
            
            # If still has issues after retries, use aggressive cleanup as last resort
            if self._has_aws_patterns(transformed_code):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Gemini transformation still has AWS patterns, applying aggressive cleanup")
                transformed_code = self._aggressive_aws_cleanup(transformed_code)
            
            # Validate syntax
            transformed_code = self._validate_and_fix_syntax(transformed_code, original_code=code)
        else:
            # Fallback to existing transformer for non-Python
            transformer = self.transformers[language]
            transformed_code = transformer.transform(code, transformation_recipe)
        
        # Get variable mapping if available
        variable_mapping = {}
        if hasattr(self.transformers.get(language), '_variable_mappings'):
            code_id = id(code)
            variable_mapping = self.transformers[language]._variable_mappings.get(code_id, {})
        
        return transformed_code, variable_mapping
    
    def _transform_with_gemini_primary(self, code: str, recipe: Dict[str, Any], retry: bool = False) -> str:
        """Use Gemini as the PRIMARY transformation engine - not as cleanup.
        
        This is the correct approach: LLM understands context and semantics,
        regex is too brittle for complex transformations.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            import google.generativeai as genai
            from config import Config
            
            if not Config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not set, falling back to regex")
                return self._fallback_regex_transform(code, recipe)
            
            genai.configure(api_key=Config.GEMINI_API_KEY)
            # Use correct model names with models/ prefix
            # Try gemini-2.5-flash (fastest), then gemini-2.5-pro (better quality)
            try:
                model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception:
                try:
                    model = genai.GenerativeModel('models/gemini-2.5-pro')
                except Exception:
                    # Fallback to older models
                    try:
                        model = genai.GenerativeModel('models/gemini-pro')
                    except Exception:
                        model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            service_type = recipe.get('service_type', '')
            target_api = recipe.get('target_api', 'GCP')
            
            # Build comprehensive prompt for direct transformation
            prompt = self._build_transformation_prompt(code, service_type, target_api, retry)
            
            # Add timeout and generation config to prevent hanging
            import google.generativeai.types as genai_types
            generation_config = genai_types.GenerationConfig(
                max_output_tokens=8192,  # Limit output size
                temperature=0.1,  # Lower temperature for more deterministic output
            )
            
            # Use asyncio timeout or threading timeout to prevent hanging
            import signal
            import threading
            
            response_result = [None]
            exception_result = [None]
            
            def generate_with_timeout():
                try:
                    response_result[0] = model.generate_content(
                        prompt,
                        generation_config=generation_config,
                        request_options={"timeout": 60}  # 60 second timeout
                    )
                except Exception as e:
                    exception_result[0] = e
            
            # Run in a thread with timeout
            thread = threading.Thread(target=generate_with_timeout)
            thread.daemon = True
            thread.start()
            thread.join(timeout=90)  # 90 second overall timeout
            
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
            transformed_code = self._extract_code_from_response(transformed_code)
            
            logger.info("Gemini primary transformation completed")
            return transformed_code
            
        except Exception as e:
            logger.warning(f"Gemini transformation failed: {e}, falling back to regex")
            return self._fallback_regex_transform(code, recipe)
    
    def _build_transformation_prompt(self, code: str, service_type: str, target_api: str, retry: bool = False) -> str:
        """Build a comprehensive prompt for Gemini to transform AWS code to GCP."""
        
        # Detect services from code
        services_detected = []
        if re.search(r'boto3\.(client|resource)\([\'\"]s3[\'\"]', code, re.IGNORECASE) or re.search(r'\.(get_object|put_object|upload_file|download_file)', code):
            services_detected.append('S3')
        if re.search(r'boto3\.(client|resource)\([\'\"]dynamodb[\'\"]', code, re.IGNORECASE) or re.search(r'\.(put_item|get_item|batch_write)', code):
            services_detected.append('DynamoDB')
        if re.search(r'boto3\.(client|resource)\([\'\"]sqs[\'\"]', code, re.IGNORECASE) or re.search(r'\.send_message', code):
            services_detected.append('SQS')
        if re.search(r'boto3\.(client|resource)\([\'\"]sns[\'\"]', code, re.IGNORECASE) or re.search(r'\.publish.*TopicArn', code):
            services_detected.append('SNS')
        if re.search(r'lambda_handler\s*\(', code, re.IGNORECASE) or re.search(r'event\[[\'"]Records[\'"]\]', code):
            services_detected.append('Lambda')
        
        services_str = ', '.join(services_detected) if services_detected else 'AWS services'
        
        retry_note = "\n\n**THIS IS A RETRY - Previous attempt still contained AWS patterns. Be EXTREMELY thorough this time.**" if retry else ""
        
        prompt = f"""You are an expert code refactoring assistant. Transform the following AWS Python code to Google Cloud Platform (GCP) code.

**CRITICAL REQUIREMENTS:**
1. **ZERO AWS CODE** - The output must contain NO AWS patterns, variables, or APIs
2. **Complete transformation** - Every AWS service call must be replaced with its GCP equivalent
3. **Correct syntax** - Output must be valid, executable Python code
4. **Proper imports** - Include all necessary GCP SDK imports
5. **Correct API usage** - Use GCP APIs correctly, not AWS patterns with GCP imports

**SERVICES DETECTED:** {services_str}

**TRANSFORMATION RULES:**

**Lambda → Cloud Functions:**
- `def lambda_handler(event, context):` → `def process_gcs_file(data, context):` (for GCS triggers)
- Remove `event['Records']` loop - GCS functions receive single file events
- `event['Records'][0]['s3']['bucket']['name']` → `data.get('bucket')`
- `event['Records'][0]['s3']['object']['key']` → `data.get('name')`
- Remove `return {{'statusCode': 200}}` - Cloud Functions don't return HTTP responses
- Replace `event` variable → `data` variable throughout
- Remove `if 's3' not in record_event:` checks

**S3 → Cloud Storage:**
- `boto3.client('s3')` → `storage.Client()`
- `s3_client = storage.Client()` → `storage_client = storage.Client()` (rename variable)
- `s3_client.get_object(Bucket=b, Key=k)` → `bucket = storage_client.bucket(b); blob = bucket.blob(k); content = blob.download_as_text()`
- `response['Body'].read().decode('utf-8')` → `blob.download_as_text()`
- `s3://` URLs → `gs://` URLs
- `storage_client.exceptions.NoSuchKey` → `from google.cloud.exceptions import NotFound`
- Remove redundant assignments like `csv_content = csv_content`

**DynamoDB → Firestore:**
- `boto3.client('dynamodb')` → `firestore.Client()`
- `dynamodb_client = boto3.client('dynamodb')` → `firestore_db = firestore.Client()`
- Function names: `batch_write_to_dynamodb` → `batch_write_to_firestore`
- `dynamodb_client.batch_write_item(RequestItems={{TABLE: batch}})` → `batch = firestore_db.batch(); collection_ref = firestore_db.collection(collection_name); for item in items: doc_ref = collection_ref.document(); batch.set(doc_ref, item); batch.commit()`
- **DO NOT create broken code** like `response = batch = firestore_db.batch()` - fix properly
- **DO NOT use invalid syntax** like `FIRESTORE_COLLECTION_NAME: batch` - use proper collection reference
- Remove DynamoDB item format `{{'S': 'value'}}` → use native Python dicts
- Batch size: 25 (DynamoDB) → 500 (Firestore)
- Remove UnprocessedItems checking logic

**SQS → Pub/Sub:**
- `boto3.client('sqs')` → `pubsub_v1.PublisherClient()`
- `sqs_client = boto3.client('sqs')` → `pubsub_publisher = pubsub_v1.PublisherClient()`
- Function names: `send_to_dlq` → `publish_error_message`
- `sqs_client.send_message(QueueUrl=url, MessageBody=body)` → `import os; topic_path = pubsub_publisher.topic_path(os.getenv('GCP_PROJECT_ID'), os.getenv('GCP_PUBSUB_TOPIC_ID')); future = pubsub_publisher.publish(topic_path, json.dumps(body).encode('utf-8')); future.result()`
- Remove `QueueUrl` parameter completely
- Use `PUB_SUB_ERROR_TOPIC` env var (full path format: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
- Remove duplicate client initialization

**SNS → Pub/Sub:**
- `boto3.client('sns')` → `pubsub_v1.PublisherClient()` (can reuse same publisher)
- `sns_client = boto3.client('sns')` → `pubsub_publisher = pubsub_v1.PublisherClient()`
- Function names: `publish_sns_summary` → `publish_summary_message`
- `sns_client.publish(TopicArn=arn, Message=msg, Subject=subj)` → `import os; topic_path = pubsub_publisher.topic_path(os.getenv('GCP_PROJECT_ID'), os.getenv('GCP_PUBSUB_TOPIC_ID')); future = pubsub_publisher.publish(topic_path, msg.encode('utf-8')); future.result()`
- **REMOVE Subject parameter** - Pub/Sub doesn't support it
- Use the global `PUB_SUB_SUMMARY_TOPIC` environment variable, don't hardcode topic paths
- Use `PUB_SUB_SUMMARY_TOPIC` env var (full path format: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)

**Environment Variables:**
- `DYNAMODB_TABLE_NAME` → `FIRESTORE_COLLECTION_NAME`
- `SQS_DLQ_URL` → `PUB_SUB_ERROR_TOPIC` (format: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
- `SNS_TOPIC_ARN` → `PUB_SUB_SUMMARY_TOPIC` (format: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
- Default values must be GCP format, NOT AWS URLs/ARNs
- Remove comments mentioning "Lambda configuration" - use "Cloud Function configuration"

**Variable Naming:**
- `s3_client` → `storage_client`
- `dynamodb_client` → `firestore_db`
- `sqs_client` → `pubsub_publisher`
- `sns_client` → `pubsub_publisher`
- `'s3_key'` → `'object_key'` or `'gcs_file'`

**Exception Handling:**
- `storage_client.exceptions.NoSuchKey` → `from google.cloud.exceptions import NotFound`
- Remove all `boto3` and `botocore` imports

**Syntax Requirements:**
- No broken assignments: `response = batch = firestore_db.batch()` → `batch = firestore_db.batch()`
- No invalid collection paths: `FIRESTORE_COLLECTION_NAME: batch` → `collection_ref = firestore_db.collection(FIRESTORE_COLLECTION_NAME)`
- No redundant assignments: `csv_content = csv_content` → remove
- No duplicate client initializations
- Proper comment formatting
- Fix broken Pub/Sub syntax: `future = pubsub_publisher.publish(...))` → `future = pubsub_publisher.publish(...)`

**Return Format:**
- Remove AWS Lambda response format: `return {{'statusCode': 200, 'body': '...'}}`
- Cloud Functions return None or raise exceptions

{retry_note}

**INPUT CODE:**
```python
{code}
```

**OUTPUT REQUIREMENTS:**
- Return ONLY the transformed Python code
- NO explanations, NO markdown formatting, NO code blocks
- Just pure, executable Python code
- Ensure ALL AWS patterns are removed
- Ensure ALL GCP APIs are used correctly

**TRANSFORMED GCP CODE:**"""
        
        return prompt
    
    def _extract_code_from_response(self, response_text: str) -> str:
        """Extract Python code from Gemini response, handling various formats."""
        # Remove markdown code blocks
        if '```python' in response_text:
            parts = response_text.split('```python')
            if len(parts) > 1:
                response_text = parts[1].split('```')[0].strip()
        elif '```' in response_text:
            parts = response_text.split('```')
            code_blocks = []
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    block = parts[i].strip()
                    if block and len(block) > 50:
                        code_blocks.append(block)
            if code_blocks:
                response_text = max(code_blocks, key=len)
        
        # Remove explanation text
        lines = response_text.split('\n')
        cleaned_lines = []
        code_started = False
        for line in lines:
            stripped = line.strip()
            if not code_started:
                if stripped.startswith(('Here', 'The', 'This', '**', '##')):
                    continue
                if stripped.startswith(('import', 'from', 'def', 'class')):
                    code_started = True
            
            if code_started or stripped:
                # Skip markdown headers
                if stripped.startswith(('##', '###', '**')) and not stripped.startswith('#'):
                    continue
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _has_aws_patterns(self, code: str) -> bool:
        """Check if code still contains AWS patterns."""
        aws_patterns = [
            r'\bboto3\b',
            r'\bdynamodb_client\b',
            r'\bsqs_client\b',
            r'\bsns_client\b',
            r'\bs3_client\b',
            r'\blambda_handler\s*\(',
            r'event\[[\'"]Records[\'"]\]',
            r'\.get_object\s*\(',
            r'\.batch_write_item\s*\(',
            r'\.send_message\s*\(',
            r'Bucket\s*=',
            r'Key\s*=',
            r'QueueUrl\s*=',
            r'TopicArn\s*=',
            r'DYNAMODB_TABLE_NAME',
            r'SQS_DLQ_URL',
            r'SNS_TOPIC_ARN',
            r'return\s+\{\s*[\'"]statusCode[\'"]',
            r'https://sqs\.',  # SQS URLs
            r'arn:aws:sns:',  # SNS ARNs
            r's3://',  # S3 URLs
            r'\'s3_key\'',  # Dictionary keys
            r'"s3_key"',
            r'batch_write_to_dynamodb',  # Function names
            r'publish_sns_summary',  # Function names
            r'send_to_dlq',  # Function names
            r'storage_client\.exceptions\.NoSuchKey',  # Wrong exception
            r'response\s*=\s*batch\s*=\s*',  # Broken syntax
            r'FIRESTORE_COLLECTION_NAME:\s*batch',  # Invalid syntax
            r'Subject\s*=',  # SNS Subject parameter
            r'json\.dumps\(json\.dumps',  # Double encoding
        ]
        
        for pattern in aws_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False
    
    def _apply_simple_regex_fixes(self, code: str) -> str:
        """Apply only simple, unambiguous regex fixes (imports, basic patterns)."""
        # Only fix imports - these are unambiguous
        code = re.sub(r'^import boto3\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3.*$', '', code, flags=re.MULTILINE)
        
        # Remove any remaining boto3 imports in comments
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            if 'import boto3' in line and line.strip().startswith('#'):
                continue
            cleaned_lines.append(line)
        code = '\n'.join(cleaned_lines)
        
        return code
    
    def _is_valid_syntax(self, code: str) -> bool:
        """Check if code has valid Python syntax."""
        try:
            import ast
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _fallback_regex_transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Fallback regex transformation if Gemini is unavailable."""
        # Use the Python transformer's auto-detect method
        if 'python' in self.transformers:
            transformer = self.transformers['python']
            if hasattr(transformer, '_auto_detect_and_migrate'):
                return transformer._auto_detect_and_migrate(code)
        # If transformer doesn't have the method, use aggressive cleanup
        return self._aggressive_aws_cleanup(code)
    
    def _aggressive_aws_cleanup(self, code: str) -> str:
        """
        AGGRESSIVE AWS cleanup that runs FIRST and catches ALL AWS patterns.
        This is the single source of truth for AWS-to-GCP conversion.
        """
        result = code
        
        # STEP 1: Replace ALL boto3.client() calls FIRST - be EXTREMELY aggressive
        # Match ANY whitespace, any quotes, any parameters
        result = re.sub(
            r'(\w+)\s*=\s*boto3\s*\.\s*client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'\1 = firestore.Client()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'(\w+)\s*=\s*boto3\s*\.\s*client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'(\w+)\s*=\s*boto3\s*\.\s*client\s*\(\s*[\'\"]sns[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'(\w+)\s*=\s*boto3\s*\.\s*client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # STEP 1.5: Also catch boto3.client() without variable assignment
        result = re.sub(
            r'boto3\s*\.\s*client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'firestore.Client()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'boto3\s*\.\s*client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            r'pubsub_v1.PublisherClient()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        result = re.sub(
            r'boto3\s*\.\s*client\s*\(\s*[\'\"]sns[\'\"][^\)]*\)',
            r'pubsub_v1.PublisherClient()',
            result,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # STEP 2: Fix variable names IMMEDIATELY after client replacement
        # Be aggressive - replace ALL occurrences
        result = re.sub(r'\bdynamodb_client\b', 'firestore_db', result)
        result = re.sub(r'\bsqs_client\b', 'pubsub_publisher', result)
        result = re.sub(r'\bsns_client\b', 'pubsub_publisher', result)
        result = re.sub(r'\bs3_client\b', 'storage_client', result)
        
        # STEP 3: Fix AWS API method calls
        # s3_client.get_object(Bucket=..., Key=...) -> bucket.blob pattern
        result = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_object\s*\(\s*Bucket\s*=\s*([^,]+),\s*Key\s*=\s*([^,\)]+)\s*\)',
            r'bucket = storage_client.bucket(\3)\n    blob = bucket.blob(\4)\n    csv_content = blob.download_as_text()',
            result,
            flags=re.DOTALL
        )
        result = re.sub(r"response\['Body'\]\.read\(\)\.decode\(['\"]utf-8['\"]\)", 'csv_content', result)
        result = re.sub(r'response\["Body"\]\.read\(\)\.decode\(["\']utf-8["\']\)', 'csv_content', result)
        
        # STEP 4: Fix lambda_handler
        result = re.sub(
            r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
            'def process_gcs_file(data, context):\n    """\n    Background Cloud Function triggered by a new file in Cloud Storage.\n    The \'data\' parameter contains the bucket and file information.\n    The \'context\' parameter provides event metadata.\n    """',
            result,
            flags=re.IGNORECASE
        )
        
        # STEP 5: Fix event['Records'] patterns
        result = re.sub(
            r'for\s+record_event\s+in\s+event\[[\'"]Records[\'"]\]\s*:',
            '# GCS background function receives single file event\n    # Process the single file event',
            result
        )
        result = re.sub(
            r'if\s+not\s+event\.get\([\'"]Records[\'"]\)\s*:',
            'if not data.get(\'bucket\') or not data.get(\'name\'):',
            result
        )
        result = re.sub(
            r'record_event\[[\'"]s3[\'"]\]\[[\'"]bucket[\'"]\]\[[\'"]name[\'"]\]',
            'data.get(\'bucket\')',
            result
        )
        result = re.sub(
            r'record_event\[[\'"]s3[\'"]\]\[[\'"]object[\'"]\]\[[\'"]key[\'"]\]',
            'data.get(\'name\')',
            result
        )
        
        # STEP 6: Fix environment variables
        result = re.sub(r'DYNAMODB_TABLE_NAME', 'FIRESTORE_COLLECTION_NAME', result)
        result = re.sub(r'SQS_DLQ_URL', 'PUB_SUB_ERROR_TOPIC', result)
        result = re.sub(r'SNS_TOPIC_ARN', 'PUB_SUB_SUMMARY_TOPIC', result)
        
        # STEP 7: Fix AWS API calls
        # dynamodb_client.batch_write_item() -> Firestore batch
        result = re.sub(
            r'(\w+)\.batch_write_item\s*\(\s*RequestItems\s*=\s*\{([^}]+)\}\s*\)',
            r'batch = firestore_db.batch()\n    collection_ref = firestore_db.collection(\2)\n    for item in items:\n        doc_ref = collection_ref.document()\n        batch.set(doc_ref, item)\n    batch.commit()',
            result,
            flags=re.DOTALL
        )
        
        # sqs_client.send_message() -> Pub/Sub publish
        result = re.sub(
            r'(\w+)\.send_message\s*\(\s*QueueUrl\s*=\s*([^,]+),\s*MessageBody\s*=\s*([^,\)]+)\s*\)',
            r'import os\n    topic_path = pubsub_publisher.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), os.getenv("GCP_PUBSUB_TOPIC_ID", "error-topic"))\n    future = pubsub_publisher.publish(topic_path, json.dumps(\3).encode("utf-8"))',
            result,
            flags=re.DOTALL
        )
        
        # sns_client.publish() -> Pub/Sub publish
        result = re.sub(
            r'(\w+)\.publish\s*\(\s*TopicArn\s*=\s*([^,]+),\s*Message\s*=\s*([^,\)]+)',
            r'import os\n    topic_path = pubsub_publisher.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), os.getenv("GCP_PUBSUB_TOPIC_ID", "summary-topic"))\n    future = pubsub_publisher.publish(topic_path, \3.encode("utf-8"))',
            result,
            flags=re.DOTALL
        )
        
        # STEP 8: Fix AWS comments
        result = re.sub(r'#\s*AWS\s+Clients?\s*', '# Google Cloud Clients', result, flags=re.IGNORECASE)
        
        # STEP 9: Ensure required imports
        if 'firestore.Client()' in result or 'firestore_db' in result:
            if 'from google.cloud import firestore' not in result:
                lines = result.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import firestore')
                result = '\n'.join(lines)
        
        if 'pubsub_v1.PublisherClient()' in result or 'pubsub_publisher' in result:
            if 'from google.cloud import pubsub_v1' not in result:
                lines = result.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import pubsub_v1')
                result = '\n'.join(lines)
        
        if 'storage.Client()' in result or 'storage_client' in result:
            if 'from google.cloud import storage' not in result:
                lines = result.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import storage')
                result = '\n'.join(lines)
        
        # STEP 10: Remove boto3 imports
        result = re.sub(r'^import boto3\s*$', '', result, flags=re.MULTILINE)
        result = re.sub(r'^from boto3.*$', '', result, flags=re.MULTILINE)
        
        return result
    
    def _validate_and_fix_syntax(self, code: str, original_code: str = None) -> str:
        """
        Validate Python syntax and attempt to fix common issues.
        Also validates that output code contains no AWS/Azure references.
        Returns syntactically correct code or raises SyntaxError.
        """
        import ast
        import logging
        logger = logging.getLogger(__name__)
        
        # Validate no AWS/Azure references in output code
        # Note: We exclude Python's 'lambda' keyword and variable names that happen to match
        # We check for actual AWS/Azure service usage, not just variable names
        aws_azure_patterns = [
            r'\bboto3\b', r'\bAWS\b(?!\w)', r'\baws\b(?!\w)', 
            r'\bS3\b(?!\w)(?!\s*[:=])', r'\bs3\b(?!\w)(?!\s*[:=])',  # S3 but not variable assignments
            r'\bLambda\b(?!\s*[:=])', r'\bDynamoDB\b(?!\s*[:=])', r'\bdynamodb\b(?!\s*[:=])',
            r'\bSQS\b(?!\s*[:=])', r'\bsqs\b(?!\s*[:=])', r'\bSNS\b(?!\s*[:=])', r'\bsns\b(?!\s*[:=])', 
            r'\bRDS\b(?!\s*[:=])', r'\brds\b(?!\s*[:=])',
            r'\bEC2\b', r'\bec2\b', r'\bCloudWatch\b', r'\bcloudwatch\b',
            r'\bAPI Gateway\b', r'\bapigateway\b', r'\bEKS\b', r'\beks\b',
            r'\bFargate\b', r'\bfargate\b', r'\bECS\b', r'\becs\b',
            r'\bAzure\b(?!\w)', r'\bazure\b(?!\w)', r'\bBlobServiceClient\b', r'\bblob_service_client\b',
            r'\bCosmosClient\b', r'\bcosmos_client\b', r'\bServiceBusClient\b',
            r'\bEventHubProducerClient\b', r'\bazure\.storage\b', r'\bazure\.functions\b',
            r'\bazure\.cosmos\b', r'\bazure\.servicebus\b', r'\bazure\.eventhub\b',
            r'\bAWS_ACCESS_KEY_ID\b', r'\bAWS_SECRET_ACCESS_KEY\b', r'\bAWS_REGION\b',
            r'\bAWS_LAMBDA_FUNCTION_NAME\b', r'\bS3_BUCKET_NAME\b', r'\bAZURE_CLIENT_ID\b',
            r'\bAZURE_CLIENT_SECRET\b', r'\bAZURE_LOCATION\b', r'\bAZURE_STORAGE_CONTAINER\b',
            r'https://sqs\.', r'https://s3\.', r'\.amazonaws\.com', r'\.blob\.core\.windows\.net',
            r'\.documents\.azure\.com'
        ]
        
        # Apply aggressive fallback replacements BEFORE validation
        # This ensures we catch patterns even if main transformation failed
        # Check for boto3 usage
        if re.search(r'\bboto3\b', code, re.IGNORECASE):
            # Replace imports
            code = re.sub(r'^import boto3\s*$', '', code, flags=re.MULTILINE)
            # First, remove region_name parameters to simplify patterns
            code = re.sub(r',\s*region_name\s*=\s*[\'"][^\'"]+[\'"]', '', code)
            code = re.sub(r'region_name\s*=\s*[\'"][^\'"]+[\'\"]\s*,', '', code)
            code = re.sub(r'region_name\s*=\s*[\'"][^\'"]+[\'"]', '', code)
            # Replace client calls with region_name/config parameters - handle multiline
            code = re.sub(r'boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', 'storage.Client()', code, flags=re.DOTALL)
            code = re.sub(r'boto3\.resource\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', 'storage.Client()', code, flags=re.DOTALL)
            code = re.sub(r'boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', 'firestore.Client()', code, flags=re.DOTALL)
            code = re.sub(r'boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)', 'pubsub_v1.PublisherClient()', code, flags=re.DOTALL)
            code = re.sub(r'boto3\.client\s*\(\s*[\'\"]lambda[\'\"][^\)]*\)', 'functions_v2.FunctionServiceClient()', code, flags=re.DOTALL)
            # Also handle variable assignments - be more aggressive
            code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', r'\1 = storage.Client()', code, flags=re.DOTALL)
            code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)', r'\1 = pubsub_v1.PublisherClient()', code, flags=re.DOTALL)
            code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', r'\1 = firestore.Client()', code, flags=re.DOTALL)
            code = re.sub(r'(\w+)\s*=\s*boto3\.resource\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', r'\1 = storage.Client()', code, flags=re.DOTALL)
            code = re.sub(r'(\w+)\s*=\s*boto3\.resource\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', r'\1 = firestore.Client()', code, flags=re.DOTALL)
            # Ensure imports are present
            if 'storage.Client()' in code and 'from google.cloud import storage' not in code:
                code = 'from google.cloud import storage\n' + code
            if 'firestore.Client()' in code and 'from google.cloud import firestore' not in code:
                code = 'from google.cloud import firestore\n' + code
            if 'pubsub_v1.PublisherClient()' in code and 'from google.cloud import pubsub_v1' not in code:
                code = 'from google.cloud import pubsub_v1\n' + code
        
        # Check for AWS/Azure references (excluding comments and strings)
        code_lines = code.split('\n')
        violations = []
        for i, line in enumerate(code_lines, 1):
            # Skip comment lines and string literals
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            # Check if line contains AWS/Azure patterns
            # Skip if line is inside a multi-line string (simple heuristic)
            if '"""' in line or "'''" in line:
                # Could be start/end of multi-line string, skip for now
                continue
            
            for pattern in aws_azure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Make sure it's not in a string literal (check for balanced quotes)
                    # If quotes are balanced, it's likely code, not a string
                    quote_count_double = line.count('"')
                    quote_count_single = line.count("'")
                    # Skip if odd number of quotes (likely inside a string)
                    if quote_count_double % 2 == 1 or quote_count_single % 2 == 1:
                        continue
                    violations.append(f"Line {i}: Found AWS/Azure reference: {pattern} in '{line.strip()}'")
                    break
        
        if violations:
            logger.warning("AWS/Azure references found in output code:")
            for violation in violations:
                logger.warning(violation)
            # Try to clean up common violations
            for pattern in aws_azure_patterns:
                # Only replace if not in strings
                code = self._safe_replace_pattern(code, pattern, '')
        
        # First, try to parse the code
        try:
            ast.parse(code)
            return code  # Code is valid
        except SyntaxError as e:
            logger.debug(f"Syntax error detected: {e}")
            logger.debug(f"Error at line {e.lineno}: {e.text}")
            logger.debug(f"Code snippet around error:\n{code[max(0, e.lineno*50-100):e.lineno*50+100]}")
            
            # Try to fix common issues
            fixed_code = self._attempt_syntax_fix(code, e)
            
            # Validate the fixed code
            try:
                ast.parse(fixed_code)
                logger.debug("Syntax fix successful")
                return fixed_code
            except SyntaxError as e2:
                logger.debug(f"Syntax fix failed: {e2}")
                # If we can't fix it, try aggressive fallback transformations
                logger.warning(f"Transformed code has syntax errors, attempting fallback fixes: {e}")
                
                # Apply fallback: at least replace boto3 imports and client calls
                fallback_code = code
                fallback_code = re.sub(r'import boto3', 'from google.cloud import storage', fallback_code)
                fallback_code = re.sub(r'boto3\.client\([\'\"]s3[\'\"]\)', 'storage.Client()', fallback_code)
                fallback_code = re.sub(r'boto3\.resource\([\'\"]s3[\'\"]\)', 'storage.Client()', fallback_code)
                fallback_code = re.sub(r'boto3\.client\([\'\"]dynamodb[\'\"]\)', 'firestore.Client()', fallback_code)
                fallback_code = re.sub(r'boto3\.client\([\'\"]sqs[\'\"]\)', 'pubsub_v1.PublisherClient()', fallback_code)
                fallback_code = re.sub(r'boto3\.client\([\'\"]lambda[\'\"]\)', 'functions_v2.FunctionServiceClient()', fallback_code)
                
                # Try to parse fallback
                try:
                    ast.parse(fallback_code)
                    logger.info("Fallback transformation successful")
                    return fallback_code
                except SyntaxError:
                    pass
                
                # Last resort: return original code but log warning
                if original_code:
                    logger.warning("Returning original code due to transformation syntax errors - manual review needed")
                    # Still try to do basic replacements even on original code
                    basic_fixed = original_code
                    basic_fixed = re.sub(r'import boto3', 'from google.cloud import storage', basic_fixed)
                    basic_fixed = re.sub(r'boto3\.client\([\'\"]s3[\'\"]\)', 'storage.Client()', basic_fixed)
                    return basic_fixed
                else:
                    # If no original code, raise error
                    raise SyntaxError(f"Transformed code is invalid and cannot be fixed: {e}")
    
    def _attempt_syntax_fix(self, code: str, syntax_error: SyntaxError) -> str:
        """
        Attempt to fix common syntax errors in transformed code.
        """
        fixed = code
        
        # Fix common indentation issues
        lines = fixed.split('\n')
        fixed_lines = []
        indent_level = 0
        in_multiline_string = False
        string_char = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Track multiline strings
            if '"""' in line or "'''" in line:
                in_multiline_string = not in_multiline_string
                string_char = '"""' if '"""' in line else "'''"
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Skip lines inside multiline strings
            if in_multiline_string:
                fixed_lines.append(line)
                continue
            
            # Fix indentation for code blocks that were inserted
            # Check if this looks like a standalone code block that should be indented
            if stripped.startswith(('import ', 'from ', 'bucket =', 'blob =', 'topic_path =', 'subscriber =', 'storage_client =', 'gcs_client =')):
                # Check if we're inside a function (previous non-empty line ends with :)
                if i > 0:
                    prev_non_empty = None
                    prev_indent = ''
                    for j in range(i-1, -1, -1):
                        if lines[j].strip() and not lines[j].strip().startswith('#'):
                            prev_non_empty = lines[j]
                            prev_indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                            break
                    if prev_non_empty and prev_non_empty.rstrip().endswith(':'):
                        # Should be indented - use the same indentation as previous line + 4 spaces
                        expected_indent = prev_indent + '    '
                        if not line.startswith(expected_indent):
                            fixed_lines.append(expected_indent + stripped)
                            continue
                    elif prev_non_empty:
                        # Use same indentation as previous non-empty line
                        if not line.startswith(prev_indent):
                            fixed_lines.append(prev_indent + stripped)
                            continue
            
            fixed_lines.append(line)
        
        fixed = '\n'.join(fixed_lines)
        
        # Remove duplicate client initializations with incorrect indentation
        # Pattern: line with excessive indentation followed by same line with correct indentation
        lines = fixed.split('\n')
        cleaned_lines = []
        seen_client_init = set()
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check if this is a duplicate client initialization
            if stripped.startswith(('gcs_client = storage.Client()', 'storage_client = storage.Client()')):
                # Check if we've seen this before
                if stripped in seen_client_init:
                    # Skip this duplicate
                    continue
                # Check if indentation is wrong (more than 12 spaces)
                indent = line[:len(line) - len(line.lstrip())]
                if len(indent) > 12:
                    # Skip this incorrectly indented duplicate
                    continue
                seen_client_init.add(stripped)
            cleaned_lines.append(line)
        fixed = '\n'.join(cleaned_lines)
        
        # Fix double assignments (e.g., "response = bucket = ...")
        fixed = re.sub(r'(\w+)\s*=\s*(\w+)\s*=\s*', r'\1 = ', fixed)
        
        # Fix malformed function calls with extra commas
        fixed = re.sub(r',\s*,', ',', fixed)
        fixed = re.sub(r'\(\s*,', '(', fixed)
        fixed = re.sub(r',\s*\)', ')', fixed)
        
        return fixed
    
    def _safe_replace_pattern(self, code: str, pattern: str, replacement: str) -> str:
        """
        Safely replace a pattern in code, avoiding string literals and comments.
        """
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            # Skip comment lines
            if line.strip().startswith('#'):
                result_lines.append(line)
                continue
            # Simple check: if line has balanced quotes, it's safe to replace
            # This is a heuristic and may not catch all cases
            if line.count('"') % 2 == 0 and line.count("'") % 2 == 0:
                # Safe to replace
                result_lines.append(re.sub(pattern, replacement, line, flags=re.IGNORECASE))
            else:
                # Might be in a string, skip
                result_lines.append(line)
        return '\n'.join(result_lines)


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
    
    def __init__(self, service_mapper):
        super().__init__(service_mapper)
        from config import config
        self.gcp_project_id = config.GCP_PROJECT_ID
        self.gcp_region = config.GCP_REGION
    
    def _get_aws_to_gcp_region_mapping(self) -> dict:
        """Get comprehensive mapping of AWS regions to Google Cloud Storage locations.
        
        Returns:
            dict: Mapping of AWS region names to GCP location names
        """
        return {
            # US Regions
            'us-east-1': 'US-EAST1',      # N. Virginia -> US East (South Carolina)
            'us-east-2': 'US-EAST4',      # Ohio -> US East (N. Virginia)
            'us-west-1': 'US-WEST1',      # N. California -> US West (Oregon)
            'us-west-2': 'US-WEST1',      # Oregon -> US West (Oregon) - closest match
            
            # Europe Regions
            'eu-west-1': 'EUROPE-WEST1',  # Ireland -> Europe West (Belgium)
            'eu-west-2': 'EUROPE-WEST2',  # London -> Europe West (London)
            'eu-west-3': 'EUROPE-WEST3',  # Paris -> Europe West (Frankfurt)
            'eu-central-1': 'EUROPE-WEST3',  # Frankfurt -> Europe West (Frankfurt)
            'eu-central-2': 'EUROPE-CENTRAL2',  # Zurich -> Europe Central (Warsaw)
            'eu-north-1': 'EUROPE-NORTH1',  # Stockholm -> Europe North (Finland)
            'eu-south-1': 'EUROPE-WEST4',  # Milan -> Europe West (Netherlands)
            'eu-south-2': 'EUROPE-WEST4',  # Spain -> Europe West (Netherlands)
            
            # Asia Pacific Regions
            'ap-southeast-1': 'ASIA-SOUTHEAST1',  # Singapore -> Asia Southeast (Singapore)
            'ap-southeast-2': 'AUSTRALIA-SOUTHEAST1',  # Sydney -> Australia Southeast (Sydney)
            'ap-southeast-3': 'ASIA-SOUTHEAST2',  # Jakarta -> Asia Southeast (Jakarta)
            'ap-southeast-4': 'AUSTRALIA-SOUTHEAST2',  # Melbourne -> Australia Southeast (Melbourne)
            'ap-southeast-5': 'ASIA-SOUTHEAST1',  # Bangkok -> Asia Southeast (Singapore) - closest
            'ap-northeast-1': 'ASIA-NORTHEAST1',  # Tokyo -> Asia Northeast (Tokyo)
            'ap-northeast-2': 'ASIA-NORTHEAST2',  # Seoul -> Asia Northeast (Osaka)
            'ap-northeast-3': 'ASIA-NORTHEAST3',  # Osaka -> Asia Northeast (Seoul)
            'ap-south-1': 'ASIA-SOUTH1',  # Mumbai -> Asia South (Mumbai)
            'ap-south-2': 'ASIA-SOUTH1',  # Hyderabad -> Asia South (Mumbai) - closest
            'ap-east-1': 'ASIA-EAST1',    # Hong Kong -> Asia East (Taiwan)
            
            # Middle East Regions
            'me-south-1': 'ASIA-SOUTH1',     # Bahrain -> Asia South (Mumbai) - closest
            'me-central-1': 'ASIA-SOUTH1',   # UAE -> Asia South (Mumbai) - closest
            'me-central-2': 'ASIA-SOUTH1',   # UAE -> Asia South (Mumbai) - closest
            
            # South America Regions
            'sa-east-1': 'SOUTHAMERICA-EAST1',  # São Paulo -> South America East (São Paulo)
            
            # Canada Regions
            'ca-central-1': 'US-EAST1',      # Montreal -> US East (South Carolina) - closest
            'ca-west-1': 'US-WEST1',      # Calgary -> US West (Oregon) - closest
            
            # Africa Regions
            'af-south-1': 'EUROPE-WEST1',  # Cape Town -> Europe West (Belgium) - closest geographically
            
            # China Regions (special handling - may need different credentials)
            'cn-north-1': 'ASIA-NORTHEAST1',  # Beijing -> Asia Northeast (Tokyo) - closest
            'cn-northwest-1': 'ASIA-NORTHEAST1',  # Ningxia -> Asia Northeast (Tokyo) - closest
            
            # Israel Regions
            'il-central-1': 'EUROPE-WEST1',  # Tel Aviv -> Europe West (Belgium) - closest
            
            # Default fallback
            'default': 'US',  # Default to US multi-region
        }
    
    def _map_aws_region_to_gcp_location(self, aws_region: str) -> str:
        """Map an AWS region to the closest GCP Cloud Storage location.
        
        Args:
            aws_region: AWS region name (e.g., 'us-east-1', 'eu-west-1')
            
        Returns:
            str: GCP location name (e.g., 'US-EAST1', 'EUROPE-WEST1')
        """
        # Normalize the AWS region (remove quotes, whitespace)
        aws_region = aws_region.strip().strip('\'"').lower()
        
        # Get the mapping
        region_map = self._get_aws_to_gcp_region_mapping()
        
        # Standard mapping
        return region_map.get(aws_region, region_map.get('default', 'US'))
    
    def transform(self, code: str, recipe: Dict[str, Any]) -> str:
        """Transform Python code based on the recipe"""
        operation = recipe.get('operation', '')
        service_type = recipe.get('service_type', '')
        
        if operation == 'service_migration' and service_type:
            # Handle specific service migration
            if service_type == 's3_to_gcs':
                transformed_code, var_mapping = self._migrate_s3_to_gcs(code)
                # Store variable mapping for later retrieval
                if not hasattr(self, '_variable_mappings'):
                    self._variable_mappings = {}
                self._variable_mappings[id(code)] = var_mapping
                return transformed_code
            elif service_type == 'lambda_to_cloud_functions':
                transformed_code, var_mapping = self._migrate_lambda_to_cloud_functions(code)
                # Store variable mapping
                if not hasattr(self, '_variable_mappings'):
                    self._variable_mappings = {}
                self._variable_mappings[id(code)] = var_mapping
                return transformed_code
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
        
        # CRITICAL FIRST PASS: Catch ALL boto3.client() patterns BEFORE anything else
        # This ensures we catch patterns like dynamodb_client = boto3.client('dynamodb')
        # BEFORE they get into the refactored code
        
        # Pattern: dynamodb_client = boto3.client('dynamodb')
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'\1 = firestore.Client()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Pattern: sqs_client = boto3.client('sqs')
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Pattern: sns_client = boto3.client('sns')
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sns[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Pattern: s3_client = boto3.client('s3') or s3 = boto3.client('s3')
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Pattern: lambda_client = boto3.client('lambda')
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]lambda[\'\"][^\)]*\)',
            r'\1 = functions_v2.FunctionServiceClient()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # CRITICAL: Fix variable names AFTER client replacement
        # Pattern: dynamodb_client = ... -> firestore_db = ...
        result_code = re.sub(r'\bdynamodb_client\s*=\s*', 'firestore_db = ', result_code)
        result_code = re.sub(r'\bdynamodb_client\.', 'firestore_db.', result_code)
        
        # Pattern: sqs_client = ... -> pubsub_publisher = ...
        result_code = re.sub(r'\bsqs_client\s*=\s*', 'pubsub_publisher = ', result_code)
        result_code = re.sub(r'\bsqs_client\.', 'pubsub_publisher.', result_code)
        
        # Pattern: sns_client = ... -> pubsub_publisher = ...
        result_code = re.sub(r'\bsns_client\s*=\s*', 'pubsub_publisher = ', result_code)
        result_code = re.sub(r'\bsns_client\.', 'pubsub_publisher.', result_code)
        
        # Pattern: s3_client = storage.Client() -> storage_client = storage.Client()
        result_code = re.sub(r'\bs3_client\s*=\s*storage\.Client\(\)', 'storage_client = storage.Client()', result_code)
        result_code = re.sub(r'\bs3_client\.', 'storage_client.', result_code)
        
        # CRITICAL: Fix AWS API method calls
        # Pattern: s3_client.get_object(Bucket=..., Key=...) -> bucket.blob pattern
        result_code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_object\s*\(\s*Bucket\s*=\s*([^,]+),\s*Key\s*=\s*([^,\)]+)\s*\)',
            r'bucket = storage_client.bucket(\3)\n    blob = bucket.blob(\4)\n    csv_content = blob.download_as_text()',
            result_code,
            flags=re.DOTALL
        )
        
        # Pattern: response['Body'].read().decode('utf-8') -> csv_content
        result_code = re.sub(r"response\['Body'\]\.read\(\)\.decode\(['\"]utf-8['\"]\)", 'csv_content', result_code)
        result_code = re.sub(r'response\["Body"\]\.read\(\)\.decode\(["\']utf-8["\']\)', 'csv_content', result_code)
        
        # CRITICAL: Fix lambda_handler
        result_code = re.sub(
            r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
            'def process_gcs_file(data, context):\n    """\n    Background Cloud Function triggered by a new file in Cloud Storage.\n    The \'data\' parameter contains the bucket and file information.\n    The \'context\' parameter provides event metadata.\n    """',
            result_code,
            flags=re.IGNORECASE
        )
        
        # CRITICAL: Fix event['Records'] patterns
        result_code = re.sub(
            r'for\s+record_event\s+in\s+event\[[\'"]Records[\'"]\]\s*:',
            '# GCS background function receives single file event, not a list\n    # Process the single file event',
            result_code
        )
        result_code = re.sub(
            r'if\s+not\s+event\.get\([\'"]Records[\'"]\)\s*:',
            'if not data.get(\'bucket\') or not data.get(\'name\'):',
            result_code
        )
        
        # CRITICAL: Fix environment variables
        result_code = re.sub(r"DYNAMODB_TABLE_NAME", 'FIRESTORE_COLLECTION_NAME', result_code)
        result_code = re.sub(r"SQS_DLQ_URL", 'PUB_SUB_ERROR_TOPIC', result_code)
        result_code = re.sub(r"SNS_TOPIC_ARN", 'PUB_SUB_SUMMARY_TOPIC', result_code)
        
        # CRITICAL: Ensure imports are present
        if 'firestore.Client()' in result_code or 'firestore_db' in result_code:
            if 'from google.cloud import firestore' not in result_code:
                lines = result_code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import firestore')
                result_code = '\n'.join(lines)
        
        if 'pubsub_v1.PublisherClient()' in result_code or 'pubsub_publisher' in result_code:
            if 'from google.cloud import pubsub_v1' not in result_code:
                lines = result_code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import pubsub_v1')
                result_code = '\n'.join(lines)
        
        if 'storage.Client()' in result_code or 'storage_client' in result_code:
            if 'from google.cloud import storage' not in result_code:
                lines = result_code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import storage')
                result_code = '\n'.join(lines)
        
        # CRITICAL: Remove boto3 import if present
        result_code = re.sub(r'^import boto3\s*$', '', result_code, flags=re.MULTILINE)
        result_code = re.sub(r'^from boto3.*$', '', result_code, flags=re.MULTILINE)
        
        services_found = []
        
        # Detect which services are present - check for actual usage patterns
        if re.search(r'boto3\.(client|resource)\([\'\"]s3[\'\"]', result_code, re.IGNORECASE) or \
           re.search(r'\.(upload_file|download_file|put_object|get_object|delete_object|list_objects)', result_code):
            services_found.append('s3')
        if re.search(r'boto3\.(client|resource)\([\'\"]lambda[\'\"]', result_code, re.IGNORECASE) or \
           'lambda_handler' in result_code or re.search(r'\.invoke\(', result_code):
            services_found.append('lambda')
        if re.search(r'boto3\.(client|resource)\([\'\"]dynamodb[\'\"]', result_code, re.IGNORECASE) or \
           re.search(r'\.(put_item|get_item|query|scan|batch_writer)', result_code):
            services_found.append('dynamodb')
        if re.search(r'boto3\.(client|resource)\([\'\"]sqs[\'\"]', result_code, re.IGNORECASE) or \
           re.search(r'\.(send_message|receive_message|delete_message)', result_code):
            services_found.append('sqs')
        if re.search(r'boto3\.(client|resource)\([\'\"]sns[\'\"]', result_code, re.IGNORECASE) or \
           re.search(r'\.(publish|subscribe)', result_code):
            services_found.append('sns')
        
        # Process in order: Lambda first (may contain S3), then S3, then others
        # Lambda handlers often contain S3 code, so process Lambda first
        if 'lambda' in services_found:
            try:
                result_code, var_mapping = self._migrate_lambda_to_cloud_functions(result_code)
                # Store variable mapping
                if not hasattr(self, '_variable_mappings'):
                    self._variable_mappings = {}
                self._variable_mappings[id(result_code)] = var_mapping
            except Exception as e:
                import logging
                logging.warning(f"Lambda migration failed: {e}")
        
        # Then process S3 (most common standalone service)
        # Check again after Lambda transformation - be more aggressive
        if 's3' in services_found or re.search(r'boto3\.(client|resource)\([\'\"]s3[\'\"]', result_code, re.IGNORECASE) or \
           re.search(r'\.(upload_file|download_file|put_object|get_object|delete_object)', result_code):
            try:
                result_code, var_mapping = self._migrate_s3_to_gcs(result_code)
                # Store variable mapping
                if not hasattr(self, '_variable_mappings'):
                    self._variable_mappings = {}
                self._variable_mappings[id(result_code)] = var_mapping
            except Exception as e:
                import logging
                logging.warning(f"S3 migration failed: {e}")
                # Fallback: at least replace boto3.client('s3')
                result_code = re.sub(r'boto3\.client\([\'\"]s3[\'\"]\)', 'storage.Client()', result_code)
                result_code = re.sub(r'boto3\.resource\([\'\"]s3[\'\"]\)', 'storage.Client()', result_code)
        
        # Process other services - check again after previous transformations
        if 'dynamodb' in services_found or re.search(r'boto3\.(client|resource)\([\'\"]dynamodb[\'\"]', result_code, re.IGNORECASE):
            try:
                result_code = self._migrate_dynamodb_to_firestore(result_code)
            except Exception as e:
                import logging
                logging.warning(f"DynamoDB migration failed: {e}")
                # Fallback
                result_code = re.sub(r'boto3\.client\([\'\"]dynamodb[\'\"]\)', 'firestore.Client()', result_code)
                result_code = re.sub(r'boto3\.resource\([\'\"]dynamodb[\'\"]\)', 'firestore.Client()', result_code)
        
        if 'sqs' in services_found or re.search(r'boto3\.(client|resource)\([\'\"]sqs[\'\"]', result_code, re.IGNORECASE):
            try:
                result_code = self._migrate_sqs_to_pubsub(result_code)
            except Exception as e:
                import logging
                logging.warning(f"SQS migration failed: {e}")
                # Fallback
                result_code = re.sub(r'boto3\.client\([\'\"]sqs[\'\"]\)', 'pubsub_v1.PublisherClient()', result_code)
        
        if 'sns' in services_found or re.search(r'boto3\.(client|resource)\([\'\"]sns[\'\"]', result_code, re.IGNORECASE):
            try:
                result_code = self._migrate_sns_to_pubsub(result_code)
            except Exception as e:
                import logging
                logging.warning(f"SNS migration failed: {e}")
                # Fallback
                result_code = re.sub(r'boto3\.client\([\'\"]sns[\'\"]\)', 'pubsub_v1.PublisherClient()', result_code)
        
        # Final cleanup: remove any remaining boto3 imports if all services migrated
        # Check if boto3 is still used (not just in comments/strings)
        lines = result_code.split('\n')
        has_boto3_usage = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if '"""' in line or "'''" in line:
                continue
            if re.search(r'\bboto3\b', line):
                has_boto3_usage = True
                break
        
        if not has_boto3_usage:
            # Remove empty import lines
            result_code = re.sub(r'^import boto3\s*$', '', result_code, flags=re.MULTILINE)
            result_code = re.sub(r'^from boto3.*$', '', result_code, flags=re.MULTILINE)
        
        # Clean up multiple blank lines
        result_code = re.sub(r'\n{3,}', '\n\n', result_code)
        
        # Final pass: ensure no boto3.client/resource calls remain
        # Handle with and without region_name parameter
        # Replace standalone calls
        result_code = re.sub(r'boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', 'storage.Client()', result_code)
        result_code = re.sub(r'boto3\.resource\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', 'storage.Client()', result_code)
        result_code = re.sub(r'boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', 'firestore.Client()', result_code)
        result_code = re.sub(r'boto3\.resource\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', 'firestore.Client()', result_code)
        result_code = re.sub(r'boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)', 'pubsub_v1.PublisherClient()', result_code)
        result_code = re.sub(r'boto3\.client\s*\(\s*[\'\"]lambda[\'\"][^\)]*\)', 'functions_v2.FunctionServiceClient()', result_code)
        # Replace with variable assignments
        result_code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', r'\1 = storage.Client()', result_code)
        result_code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)', r'\1 = pubsub_v1.PublisherClient()', result_code)
        result_code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', r'\1 = firestore.Client()', result_code)
        result_code = re.sub(r'(\w+)\s*=\s*boto3\.resource\s*\(\s*[\'\"]s3[\'\"][^\)]*\)', r'\1 = storage.Client()', result_code)
        result_code = re.sub(r'(\w+)\s*=\s*boto3\.resource\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)', r'\1 = firestore.Client()', result_code)
        
        # AGGRESSIVE CLEANUP: Fix variable names that were incorrectly assigned
        # Pattern: s3_client = storage.Client() -> storage_client = storage.Client()
        result_code = re.sub(r'\bs3_client\s*=\s*storage\.Client\(\)', 'storage_client = storage.Client()', result_code)
        # Pattern: s3_client.get_object(...) -> Fix to use bucket.blob pattern
        # This should have been caught by S3 migration, but ensure it's fixed
        result_code = re.sub(
            r'(\w+)\s*=\s*s3_client\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            r'bucket = storage_client.bucket(\2)\n    blob = bucket.blob(\3)\n    csv_content = blob.download_as_text()',
            result_code
        )
        # Pattern: response = s3_client.get_object(...) -> Fix
        result_code = re.sub(
            r'response\s*=\s*s3_client\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            r'bucket = storage_client.bucket(\1)\n    blob = bucket.blob(\2)\n    csv_content = blob.download_as_text()',
            result_code
        )
        # Pattern: Replace s3_client. method calls with storage_client.
        result_code = re.sub(r'\bs3_client\.', 'storage_client.', result_code)
        
        # AGGRESSIVE: Fix DynamoDB client assignments that weren't caught
        # Pattern: dynamodb_client = boto3.client('dynamodb') -> firestore_db = firestore.Client()
        result_code = re.sub(
            r'dynamodb_client\s*=\s*boto3\.client\([\'\"]dynamodb[\'\"][^\)]*\)',
            'firestore_db = firestore.Client()',
            result_code,
            flags=re.DOTALL
        )
        # Pattern: dynamodb_client = ... -> firestore_db = ...
        result_code = re.sub(r'\bdynamodb_client\s*=\s*', 'firestore_db = ', result_code)
        # Pattern: dynamodb_client. method calls -> firestore_db.
        result_code = re.sub(r'\bdynamodb_client\.', 'firestore_db.', result_code)
        
        # AGGRESSIVE: Fix SQS client assignments
        # Pattern: sqs_client = boto3.client('sqs') -> pubsub_publisher = pubsub_v1.PublisherClient()
        result_code = re.sub(
            r'sqs_client\s*=\s*boto3\.client\([\'\"]sqs[\'\"][^\)]*\)',
            'pubsub_publisher = pubsub_v1.PublisherClient()',
            result_code,
            flags=re.DOTALL
        )
        # Pattern: sqs_client = ... -> pubsub_publisher = ...
        result_code = re.sub(r'\bsqs_client\s*=\s*', 'pubsub_publisher = ', result_code)
        # Pattern: sqs_client. method calls -> pubsub_publisher.
        result_code = re.sub(r'\bsqs_client\.', 'pubsub_publisher.', result_code)
        
        # AGGRESSIVE: Fix SNS client assignments
        # Pattern: sns_client = boto3.client('sns') -> pubsub_publisher = pubsub_v1.PublisherClient()
        result_code = re.sub(
            r'sns_client\s*=\s*boto3\.client\([\'\"]sns[\'\"][^\)]*\)',
            'pubsub_publisher = pubsub_v1.PublisherClient()',
            result_code,
            flags=re.DOTALL
        )
        # Pattern: sns_client = ... -> pubsub_publisher = ...
        result_code = re.sub(r'\bsns_client\s*=\s*', 'pubsub_publisher = ', result_code)
        # Pattern: sns_client. method calls -> pubsub_publisher.
        result_code = re.sub(r'\bsns_client\.', 'pubsub_publisher.', result_code)
        
        # AGGRESSIVE: Fix environment variable names
        result_code = re.sub(r"DYNAMODB_TABLE_NAME", 'FIRESTORE_COLLECTION_NAME', result_code)
        result_code = re.sub(r"SQS_DLQ_URL", 'PUB_SUB_ERROR_TOPIC', result_code)
        result_code = re.sub(r"SNS_TOPIC_ARN", 'PUB_SUB_SUMMARY_TOPIC', result_code)
        
        # AGGRESSIVE: Fix AWS API method calls that weren't caught
        # Pattern: s3_client.get_object(Bucket=..., Key=...) -> bucket.blob pattern
        result_code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            r'bucket = storage_client.bucket(\3)\n    blob = bucket.blob(\4)\n    csv_content = blob.download_as_text()',
            result_code
        )
        # Pattern: response['Body'].read().decode('utf-8') -> csv_content
        result_code = re.sub(r"response\['Body'\]\.read\(\)\.decode\(['\"]utf-8['\"]\)", 'csv_content', result_code)
        result_code = re.sub(r'response\["Body"\]\.read\(\)\.decode\(["\']utf-8["\']\)', 'csv_content', result_code)
        
        # AGGRESSIVE: Fix lambda_handler if still present
        result_code = re.sub(
            r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
            'def process_gcs_file(data, context):\n    """\n    Background Cloud Function triggered by a new file in Cloud Storage.\n    The \'data\' parameter contains the bucket and file information.\n    The \'context\' parameter provides event metadata.\n    """',
            result_code,
            flags=re.IGNORECASE
        )
        
        # AGGRESSIVE: Fix event['Records'] patterns
        result_code = re.sub(
            r'for\s+record_event\s+in\s+event\[[\'"]Records[\'"]\]\s*:',
            '# GCS background function receives single file event, not a list\n    # Process the single file event',
            result_code
        )
        result_code = re.sub(
            r'if\s+not\s+event\.get\([\'"]Records[\'"]\)\s*:',
            'if not data.get(\'bucket\') or not data.get(\'name\'):',
            result_code
        )
        
        # AGGRESSIVE: Remove AWS comments
        result_code = re.sub(r'#\s*AWS\s+Clients?\s*', '# Google Cloud Clients', result_code, flags=re.IGNORECASE)
        result_code = re.sub(r'#\s*AWS\s+.*', '', result_code, flags=re.IGNORECASE)
        
        # AGGRESSIVE: Ensure required imports are present
        if 'storage_client' in result_code or 'storage.Client()' in result_code:
            if 'from google.cloud import storage' not in result_code:
                # Add import at the top
                lines = result_code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import storage')
                result_code = '\n'.join(lines)
        
        if 'firestore_db' in result_code or 'firestore.Client()' in result_code:
            if 'from google.cloud import firestore' not in result_code:
                lines = result_code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import firestore')
                result_code = '\n'.join(lines)
        
        if 'pubsub_publisher' in result_code or 'pubsub_v1' in result_code:
            if 'from google.cloud import pubsub_v1' not in result_code:
                lines = result_code.split('\n')
                import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_idx = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                lines.insert(import_idx, 'from google.cloud import pubsub_v1')
                result_code = '\n'.join(lines)
        
        # Final cleanup: remove boto3 import if no boto3 usage remains
        lines = result_code.split('\n')
        has_boto3_usage = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if '"""' in line or "'''" in line:
                continue
            if re.search(r'\bboto3\b', line) and not stripped.startswith('import'):
                has_boto3_usage = True
                break
        
        if not has_boto3_usage:
            result_code = re.sub(r'^import boto3\s*$', '', result_code, flags=re.MULTILINE)
            result_code = re.sub(r'^from boto3.*$', '', result_code, flags=re.MULTILINE)
        
        # FINAL AGGRESSIVE PASS: Catch ANY remaining AWS patterns before Gemini
        # This is a safety net to ensure we catch everything
        
        # Catch any remaining boto3.client() calls
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'\1 = firestore.Client()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sns[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        result_code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            result_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Catch any remaining AWS variable names
        result_code = re.sub(r'\bdynamodb_client\b', 'firestore_db', result_code)
        result_code = re.sub(r'\bsqs_client\b', 'pubsub_publisher', result_code)
        result_code = re.sub(r'\bsns_client\b', 'pubsub_publisher', result_code)
        result_code = re.sub(r'\bs3_client\b', 'storage_client', result_code)
        
        # Catch any remaining AWS API calls
        result_code = re.sub(
            r'(\w+)\.get_object\s*\(\s*Bucket\s*=\s*([^,]+),\s*Key\s*=\s*([^,\)]+)\s*\)',
            r'bucket = storage_client.bucket(\2)\n    blob = bucket.blob(\3)\n    csv_content = blob.download_as_text()',
            result_code,
            flags=re.DOTALL
        )
        
        # Catch any remaining lambda_handler
        result_code = re.sub(
            r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
            'def process_gcs_file(data, context):\n    """\n    Background Cloud Function triggered by a new file in Cloud Storage.\n    The \'data\' parameter contains the bucket and file information.\n    The \'context\' parameter provides event metadata.\n    """',
            result_code,
            flags=re.IGNORECASE
        )
        
        # IMPORTANT: After all service migrations, use Gemini to validate and fix any remaining AWS patterns
        # This ensures complete transformation for multi-service code
        # ALWAYS run Gemini validation - it's safer to over-validate
        result_code = self._validate_and_fix_with_gemini(result_code, code)

        return result_code
    
    def _get_aws_to_gcp_region_mapping(self) -> dict:
        """Get comprehensive mapping of AWS regions to Google Cloud Storage locations.
        
        Returns:
            dict: Mapping of AWS region names to GCP location names
        """
        return {
            # US Regions
            'us-east-1': 'US-EAST1',      # N. Virginia -> US East (South Carolina)
            'us-east-2': 'US-EAST4',      # Ohio -> US East (N. Virginia)
            'us-west-1': 'US-WEST1',      # N. California -> US West (Oregon)
            'us-west-2': 'US-WEST1',      # Oregon -> US West (Oregon) - closest match
            
            # Europe Regions
            'eu-west-1': 'EUROPE-WEST1',  # Ireland -> Europe West (Belgium)
            'eu-west-2': 'EUROPE-WEST2',  # London -> Europe West (London)
            'eu-west-3': 'EUROPE-WEST3',  # Paris -> Europe West (Frankfurt)
            'eu-central-1': 'EUROPE-WEST3',  # Frankfurt -> Europe West (Frankfurt)
            'eu-central-2': 'EUROPE-CENTRAL2',  # Zurich -> Europe Central (Warsaw)
            'eu-north-1': 'EUROPE-NORTH1',  # Stockholm -> Europe North (Finland)
            'eu-south-1': 'EUROPE-WEST4',  # Milan -> Europe West (Netherlands)
            'eu-south-2': 'EUROPE-WEST4',  # Spain -> Europe West (Netherlands)
            
            # Asia Pacific Regions
            'ap-southeast-1': 'ASIA-SOUTHEAST1',  # Singapore -> Asia Southeast (Singapore)
            'ap-southeast-2': 'AUSTRALIA-SOUTHEAST1',  # Sydney -> Australia Southeast (Sydney)
            'ap-southeast-3': 'ASIA-SOUTHEAST2',  # Jakarta -> Asia Southeast (Jakarta)
            'ap-southeast-4': 'AUSTRALIA-SOUTHEAST2',  # Melbourne -> Australia Southeast (Melbourne)
            'ap-southeast-5': 'ASIA-SOUTHEAST1',  # Bangkok -> Asia Southeast (Singapore) - closest
            'ap-northeast-1': 'ASIA-NORTHEAST1',  # Tokyo -> Asia Northeast (Tokyo)
            'ap-northeast-2': 'ASIA-NORTHEAST2',  # Seoul -> Asia Northeast (Osaka)
            'ap-northeast-3': 'ASIA-NORTHEAST3',  # Osaka -> Asia Northeast (Seoul)
            'ap-south-1': 'ASIA-SOUTH1',  # Mumbai -> Asia South (Mumbai)
            'ap-south-2': 'ASIA-SOUTH1',  # Hyderabad -> Asia South (Mumbai) - closest
            'ap-east-1': 'ASIA-EAST1',    # Hong Kong -> Asia East (Taiwan)
            
            # Middle East Regions
            'me-south-1': 'ASIA-SOUTH1',     # Bahrain -> Asia South (Mumbai) - closest
            'me-central-1': 'ASIA-SOUTH1',   # UAE -> Asia South (Mumbai) - closest
            'me-central-2': 'ASIA-SOUTH1',   # UAE -> Asia South (Mumbai) - closest
            
            # South America Regions
            'sa-east-1': 'SOUTHAMERICA-EAST1',  # São Paulo -> South America East (São Paulo)
            
            # Canada Regions
            'ca-central-1': 'US-EAST1',      # Montreal -> US East (South Carolina) - closest
            'ca-west-1': 'US-WEST1',      # Calgary -> US West (Oregon) - closest
            
            # Africa Regions
            'af-south-1': 'EUROPE-WEST1',  # Cape Town -> Europe West (Belgium) - closest geographically
            
            # China Regions (special handling - may need different credentials)
            'cn-north-1': 'ASIA-NORTHEAST1',  # Beijing -> Asia Northeast (Tokyo) - closest
            'cn-northwest-1': 'ASIA-NORTHEAST1',  # Ningxia -> Asia Northeast (Tokyo) - closest
            
            # Israel Regions
            'il-central-1': 'EUROPE-WEST1',  # Tel Aviv -> Europe West (Belgium) - closest
            
            # Default fallback
            'default': 'US',  # Default to US multi-region
        }
    
    def _map_aws_region_to_gcp_location(self, aws_region: str) -> str:
        """Map an AWS region to the closest GCP Cloud Storage location.
        
        Args:
            aws_region: AWS region name (e.g., 'us-east-1', 'eu-west-1')
            
        Returns:
            str: GCP location name (e.g., 'US-EAST1', 'EUROPE-WEST1')
        """
        # Normalize the AWS region (remove quotes, whitespace)
        aws_region = aws_region.strip().strip('\'"').lower()
        
        # Get the mapping
        region_map = self._get_aws_to_gcp_region_mapping()
        
        # Standard mapping
        return region_map.get(aws_region, region_map.get('default', 'US'))
    
    def _migrate_s3_to_gcs(self, code: str) -> tuple[str, dict]:
        """Migrate AWS S3 to Google Cloud Storage with improved structure and variable naming.
        
        Returns:
            tuple: (transformed_code, variable_mapping) where variable_mapping is a dict
                   mapping old variable names to new variable names
        """
        variable_mapping = {}  # Track ALL variable name changes for GCP-friendly naming
        
        # First pass: Identify ALL AWS-related variables BEFORE any transformation
        # Store original code for variable detection
        original_code = code
        
        # Pattern 1: Client variables (s3, s3_client, client when used with boto3.client('s3'))
        client_pattern = r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"].*?\)'
        client_matches = re.finditer(client_pattern, original_code, flags=re.DOTALL)
        for match in client_matches:
            var_name = match.group(1)
            if var_name not in variable_mapping:
                variable_mapping[var_name] = 'gcs_client'
        
        # Pattern 2: Response variables from S3 list operations
        response_pattern = r'(\w+)\s*=\s*(\w+)\.list_objects(?:_v2)?\('
        response_matches = re.finditer(response_pattern, original_code)
        for match in response_matches:
            response_var = match.group(1)
            client_var = match.group(2)
            # Only track if the client variable is an S3 client
            if (client_var in variable_mapping or 's3' in client_var.lower() or 
                re.search(rf'\b{re.escape(client_var)}\s*=\s*boto3\.client', original_code)):
                if response_var not in variable_mapping and response_var not in ['blobs', 'bucket']:
                    # Rename typical response variable names
                    if response_var in ['response', 'result', 'objects', 'items', 'list_result']:
                        variable_mapping[response_var] = 'blobs'
        
        # Pattern 3: Common AWS variable names (s3_bucket, s3_key, s3_object, etc.)
        if re.search(r'\bs3_bucket\b', original_code):
            variable_mapping['s3_bucket'] = 'gcs_bucket'
        if re.search(r'\bs3_key\b', original_code):
            variable_mapping['s3_key'] = 'blob_name'
        if re.search(r'\bs3_object\b', original_code):
            variable_mapping['s3_object'] = 'blob'
        if re.search(r'\bs3_client\b', original_code):
            variable_mapping['s3_client'] = 'gcs_client'
        if re.search(r'\bs3\b(?=\s*\.)', original_code):
            variable_mapping['s3'] = 'gcs_client'
        
        # Pattern 4: Loop variables (obj in S3 contexts)
        if re.search(r'for\s+obj\s+in', original_code):
            variable_mapping['obj'] = 'blob'
        
        # Replace boto3 imports with GCS imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import storage', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import storage', code, flags=re.MULTILINE)
        
        # IMPORTANT: Replace S3 API method calls BEFORE client variable renaming
        # This ensures we catch patterns like s3.create_bucket() before s3 is renamed to gcs_client
        
        # Replace S3 create_bucket -> GCS bucket.create() FIRST (before variable renaming)
        # Pattern: s3.create_bucket(Bucket='bucket-name', CreateBucketConfiguration={'LocationConstraint': 'us-east-1'})
        def replace_create_bucket_early(match):
            full_match = match.group(0)
            # Extract bucket name - could be a variable name or string literal
            bucket_name_expr = match.group(2).strip()
            
            # Extract location from CreateBucketConfiguration if present
            location = None
            location_config_match = re.search(r'CreateBucketConfiguration\s*=\s*\{[^}]*LocationConstraint[^}]*:\s*([^,}]+)', full_match)
            if location_config_match:
                location_value = location_config_match.group(1).strip().strip('\'"')
                # Map AWS regions to GCP locations using comprehensive mapping
                location = self._map_aws_region_to_gcp_location(location_value)
            
            # Check for region parameter in function signature (if location not found)
            if location is None:
                region_match = re.search(r'region\s*=\s*[\'"]([^\'"]+)[\'"]', code)
                if region_match:
                    aws_region = region_match.group(1)
                    location = self._map_aws_region_to_gcp_location(aws_region)
            
            # bucket_name_expr might be a variable name (like bucket_name) or a string literal
            # Keep it as-is if it's a variable, otherwise ensure it's a string
            if bucket_name_expr.startswith("'") or bucket_name_expr.startswith('"'):
                bucket_name_str = bucket_name_expr  # Already a string literal
            else:
                bucket_name_str = bucket_name_expr  # Variable name - use as-is
            
            # Build replacement code - use correct GCS API: storage_client.create_bucket(bucket_name, location=location)
            if location:
                return f'storage_client = storage.Client()\nbucket = storage_client.create_bucket({bucket_name_str}, location=\'{location}\')\nprint(f"Bucket \'{{bucket.name}}\' created successfully in location \'{location}\'.")'
            else:
                return f'storage_client = storage.Client()\nbucket = storage_client.create_bucket({bucket_name_str})\nprint(f"Bucket \'{{bucket.name}}\' created successfully.")'
        
        # Match create_bucket BEFORE variable renaming
        # Handle: s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        # Use a more robust approach: match the entire create_bucket call and parse it manually
        def replace_create_bucket_robust(match):
            full_match = match.group(0)
            client_var = match.group(1)
            
            # Extract bucket name - could be Bucket=bucket_name or just bucket_name
            bucket_match = re.search(r'Bucket\s*=\s*([^,)]+)', full_match)
            if bucket_match:
                bucket_name_expr = bucket_match.group(1).strip()
            else:
                # Try to extract first parameter if Bucket= is not present
                param_match = re.search(r'create_bucket\(\s*([^,)]+)', full_match)
                bucket_name_expr = param_match.group(1).strip() if param_match else 'bucket_name'
            
            # Extract location from CreateBucketConfiguration
            location = None
            config_match = re.search(r'CreateBucketConfiguration\s*=\s*\{([^}]+)\}', full_match)
            if config_match:
                config_content = config_match.group(1)
                location_match = re.search(r'LocationConstraint\s*:\s*([^,}]+)', config_content)
                if location_match:
                    location_value = location_match.group(1).strip().strip('\'"')
                    # If it's a string literal, map it directly
                    if location_value and (location_value.startswith("'") or location_value.startswith('"')):
                        location_value = location_value.strip('\'"')
                        location = self._map_aws_region_to_gcp_location(location_value)
                    else:
                        # It's a variable - try to find its value
                        var_name = location_value.strip()
                        var_match = re.search(rf'{re.escape(var_name)}\s*=\s*[\'"]([^\'"]+)[\'"]', code)
                        if var_match:
                            aws_region = var_match.group(1)
                            location = self._map_aws_region_to_gcp_location(aws_region)
            
            # Check function parameter default value if location still not found
            if location is None:
                region_match = re.search(r'region\s*=\s*[\'"]([^\'"]+)[\'"]', code)
                if region_match:
                    aws_region = region_match.group(1)
                    location = self._map_aws_region_to_gcp_location(aws_region)
            
            # Preserve bucket_name_expr as-is (variable or string literal)
            bucket_name_str = bucket_name_expr.strip()
            
            # Build replacement - preserve indentation by detecting it from the original line
            lines = code.split('\n')
            indent = ''
            for line in lines:
                if full_match.strip() in line:
                    # Extract indentation from the line containing the match
                    indent = line[:len(line) - len(line.lstrip())]
                    break
            
            if location:
                # Correct GCS API: storage_client.create_bucket(bucket_name, location=location)
                replacement = f'{indent}storage_client = storage.Client()\n{indent}bucket = storage_client.create_bucket({bucket_name_str}, location=\'{location}\')\n{indent}print(f"Bucket \'{{bucket.name}}\' created successfully in location \'{location}\'.")'
            else:
                # Default location is 'US' for GCS
                replacement = f'{indent}storage_client = storage.Client()\n{indent}bucket = storage_client.create_bucket({bucket_name_str})\n{indent}print(f"Bucket \'{{bucket.name}}\' created successfully.")'
            
            return replacement
        
        # Match create_bucket with Bucket parameter and optional CreateBucketConfiguration
        # Use a balanced parentheses approach to handle nested structures properly
        def find_balanced_parens(text, start_pos):
            """Find the position of the matching closing paren for an opening paren."""
            depth = 0
            pos = start_pos
            while pos < len(text):
                if text[pos] == '(':
                    depth += 1
                elif text[pos] == ')':
                    depth -= 1
                    if depth == 0:
                        return pos
                pos += 1
            return -1
        
        # Find and replace all create_bucket calls using balanced parentheses
        create_bucket_pattern = r'(\w+)\.create_bucket\('
        matches = list(re.finditer(create_bucket_pattern, code))
        # Process matches in reverse order to avoid index shifting issues
        for match in reversed(matches):
            start_pos = match.end() - 1  # Position of opening paren
            end_pos = find_balanced_parens(code, start_pos)
            if end_pos > 0:
                full_call = code[match.start():end_pos+1]
                # Extract information from the full call
                client_var = match.group(1)
                
                # Extract bucket name
                bucket_match = re.search(r'Bucket\s*=\s*([^,)]+)', full_call)
                if bucket_match:
                    bucket_name_expr = bucket_match.group(1).strip()
                else:
                    # Try first parameter
                    param_match = re.search(r'create_bucket\(\s*([^,)]+)', full_call)
                    bucket_name_expr = param_match.group(1).strip() if param_match else 'bucket_name'
                
                # Extract location from CreateBucketConfiguration
                location = None
                config_match = re.search(r'CreateBucketConfiguration\s*=\s*\{([^}]+)\}', full_call)
                if config_match:
                    config_content = config_match.group(1)
                    location_match = re.search(r'LocationConstraint\s*:\s*([^,}]+)', config_content)
                    if location_match:
                        location_value = location_match.group(1).strip().strip('\'"')
                        if location_value and (location_value.startswith("'") or location_value.startswith('"')):
                            location_value = location_value.strip('\'"')
                            location = self._map_aws_region_to_gcp_location(location_value)
                        else:
                            # Variable - find its value
                            var_name = location_value.strip()
                            var_match = re.search(rf'{re.escape(var_name)}\s*=\s*[\'"]([^\'"]+)[\'"]', code)
                            if var_match:
                                aws_region = var_match.group(1)
                                location = self._map_aws_region_to_gcp_location(aws_region)
                
                # Check function parameter default
                if location is None:
                    region_match = re.search(r'region\s*=\s*[\'"]([^\'"]+)[\'"]', code)
                    if region_match:
                        aws_region = region_match.group(1)
                        location = self._map_aws_region_to_gcp_location(aws_region)
                
                # Get indentation from the line containing the match
                # Find the line number where the match occurs
                line_start = code.rfind('\n', 0, match.start())
                if line_start == -1:
                    line_start = 0
                else:
                    line_start += 1  # Skip the newline
                # Get the full line containing the match
                line_end = code.find('\n', match.start())
                if line_end == -1:
                    line_end = len(code)
                match_line = code[line_start:line_end]
                # Extract indentation from the line containing the match
                indent = match_line[:len(match_line) - len(match_line.lstrip())]
                
                # Build replacement - check if storage_client or gcs_client already exists in scope
                # If gcs_client exists, reuse it; otherwise create storage_client
                bucket_name_str = bucket_name_expr.strip()
                # Check if we already have a storage client variable in the current scope
                # Look for client initialization in the lines before the match
                lines_before = code[:match.start()].split('\n')
                has_storage_client = False
                client_var_name = 'storage_client'
                for line in reversed(lines_before):
                    if 'storage_client = storage.Client()' in line:
                        has_storage_client = True
                        client_var_name = 'storage_client'
                        break
                    elif 'gcs_client = storage.Client()' in line:
                        has_storage_client = True
                        client_var_name = 'gcs_client'
                        break
                
                if location:
                    # Correct GCS API: storage_client.create_bucket(bucket_name, location=location)
                    if has_storage_client:
                        # Reuse existing client
                        replacement = f'{indent}bucket = {client_var_name}.create_bucket({bucket_name_str}, location=\'{location}\')\n{indent}print(f"Bucket \'{{bucket.name}}\' created successfully in location \'{location}\'.")'
                    else:
                        # Create new client - use storage_client for consistency
                        replacement = f'{indent}storage_client = storage.Client()\n{indent}bucket = storage_client.create_bucket({bucket_name_str}, location=\'{location}\')\n{indent}print(f"Bucket \'{{bucket.name}}\' created successfully in location \'{location}\'.")'
                else:
                    # Default location is 'US' for GCS
                    if has_storage_client:
                        replacement = f'{indent}bucket = {client_var_name}.create_bucket({bucket_name_str})\n{indent}print(f"Bucket \'{{bucket.name}}\' created successfully.")'
                    else:
                        replacement = f'{indent}storage_client = storage.Client()\n{indent}bucket = storage_client.create_bucket({bucket_name_str})\n{indent}print(f"Bucket \'{{bucket.name}}\' created successfully.")'
                
                # Remove the old print statement that follows the create_bucket call
                # Find and remove the next line if it's the old AWS print statement
                lines_after = code[end_pos+1:].split('\n')
                # Check if the first non-empty line after the create_bucket call is the old AWS print statement
                if lines_after and len(lines_after) > 0:
                    # Find the first non-empty line
                    first_non_empty_idx = 0
                    for idx, line in enumerate(lines_after):
                        if line.strip() and not line.strip().startswith('#'):
                            first_non_empty_idx = idx
                            break
                    first_line_after = lines_after[first_non_empty_idx].strip() if first_non_empty_idx < len(lines_after) else ''
                    # Check if it's the old AWS print statement about region
                    if 'created successfully in region' in first_line_after or ('print' in first_line_after and 'region' in first_line_after and 'location' not in first_line_after):
                        # Remove the old print line
                        remaining_lines = lines_after[:first_non_empty_idx] + lines_after[first_non_empty_idx+1:]
                        code = code[:match.start()] + replacement + '\n'.join(remaining_lines)
                    else:
                        code = code[:match.start()] + replacement + code[end_pos+1:]
                else:
                    code = code[:match.start()] + replacement + code[end_pos+1:]
                
                # Remove any duplicate client initializations that might have been created
                # This happens if boto3.client replacement also ran
                lines = code.split('\n')
                cleaned_lines = []
                seen_storage_client = False
                seen_gcs_client = False
                for line in lines:
                    stripped = line.strip()
                    indent = line[:len(line) - len(line.lstrip())]
                    # Check for storage_client duplicates
                    if stripped == 'storage_client = storage.Client()':
                        if seen_storage_client:
                            # Skip duplicate
                            continue
                        # Check indentation - should be 8 spaces (inside try block), not 16
                        if len(indent) > 12:
                            # Wrong indentation - skip
                            continue
                        seen_storage_client = True
                    # Check for gcs_client duplicates
                    elif stripped == 'gcs_client = storage.Client()':
                        if seen_gcs_client:
                            # Skip duplicate
                            continue
                        # Check indentation - should be 8 spaces (inside try block), not 16
                        if len(indent) > 12:
                            # Wrong indentation - skip
                            continue
                        seen_gcs_client = True
                    cleaned_lines.append(line)
                code = '\n'.join(cleaned_lines)
                
                # If gcs_client exists but storage_client is referenced, replace storage_client with gcs_client
                if 'gcs_client = storage.Client()' in code and 'storage_client.create_bucket' in code:
                    code = code.replace('storage_client.create_bucket', 'gcs_client.create_bucket')
                if 'gcs_client = storage.Client()' in code and 'storage_client.bucket' in code:
                    code = code.replace('storage_client.bucket', 'gcs_client.bucket')
                if 'gcs_client = storage.Client()' in code and 'storage_client.list_blobs' in code:
                    code = code.replace('storage_client.list_blobs', 'gcs_client.list_blobs')
                if 'gcs_client = storage.Client()' in code and 'storage_client.get_bucket' in code:
                    code = code.replace('storage_client.get_bucket', 'gcs_client.get_bucket')
        
        # Also handle simple cases without CreateBucketConfiguration (fallback)
        # Match: s3.create_bucket('bucket-name') or s3.create_bucket(Bucket='name')
        code = re.sub(
            r'(\w+)\.create_bucket\(\s*([^,\)]+)\s*\)',
            replace_create_bucket_early,
            code
        )
        
        # Replace boto3.resource('s3') pattern - handle with region_name too
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.resource\([\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace boto3.client('s3') pattern - handle with region_name and config too
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Extract bucket and file names from the code to create named variables
        # Try to extract from various S3 operation patterns
        bucket_names = set()
        file_names = set()
        
        # Extract from upload_file pattern
        upload_pattern = r'\.upload_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)'
        upload_matches = re.findall(upload_pattern, code)
        if upload_matches:
            bucket_names.add(upload_matches[0][1])
            file_names.add(upload_matches[0][0])  # local file
            file_names.add(upload_matches[0][2])   # remote file
        
        # Extract from download_file pattern
        download_pattern = r'\.download_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)'
        download_matches = re.findall(download_pattern, code)
        if download_matches:
            bucket_names.add(download_matches[0][0])
            file_names.add(download_matches[0][1])  # remote file
            file_names.add(download_matches[0][2])  # local file
        
        # Extract from put_object/get_object/delete_object patterns
        put_object_pattern = r'\.put_object\(Bucket=([^,]+),\s*Key=([^,]+)'
        put_matches = re.findall(put_object_pattern, code)
        if put_matches:
            bucket_names.add(put_matches[0][0].strip('\'"'))
            file_names.add(put_matches[0][1].strip('\'"'))
        
        get_object_pattern = r'\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)'
        get_matches = re.findall(get_object_pattern, code)
        if get_matches:
            bucket_names.add(get_matches[0][0].strip('\'"'))
            file_names.add(get_matches[0][1].strip('\'"'))
        
        delete_object_pattern = r'\.delete_object\(Bucket=([^,]+),\s*Key=([^,\)]+)'
        delete_matches = re.findall(delete_object_pattern, code)
        if delete_matches:
            bucket_names.add(delete_matches[0][0].strip('\'"'))
            file_names.add(delete_matches[0][1].strip('\'"'))
        
        # Extract from list_objects patterns
        list_pattern = r'\.list_objects(?:_v2)?\(Bucket=([^,\)]+)'
        list_matches = re.findall(list_pattern, code)
        if list_matches:
            bucket_names.add(list_matches[0].strip('\'"'))
        
        # Extract from create_bucket/delete_bucket
        bucket_pattern = r'\.(?:create|delete)_bucket\(Bucket=([^,\)]+)'
        bucket_matches = re.findall(bucket_pattern, code)
        if bucket_matches:
            bucket_names.add(bucket_matches[0].strip('\'"'))
        
        # Filter bucket names (simple names without paths, not Python keywords)
        likely_buckets = [b for b in bucket_names if '/' not in b and len(b) < 50 and b not in ['s3', 'client', 'storage']]
        bucket_name = likely_buckets[0] if likely_buckets else "my-bucket"
        
        # Determine file names
        file_list = list(file_names)
        local_upload_file = file_list[0] if len(file_list) > 0 else "local_file.txt"
        remote_file_name = file_list[1] if len(file_list) > 1 else file_list[0] if len(file_list) > 0 else "remote_file.txt"
        local_download_file = file_list[2] if len(file_list) > 2 else "downloaded_file.txt"
        
        # Use bucket name from first operation found
        if upload_matches:
            bucket_name = upload_matches[0][1]
        elif download_matches:
            bucket_name = download_matches[0][0]
        elif put_matches:
            bucket_name = put_matches[0][0].strip('\'"')
        elif get_matches:
            bucket_name = get_matches[0][0].strip('\'"')
        elif list_matches:
            bucket_name = list_matches[0].strip('\'"')
        
        # Replace client instantiation - handle various formats
        # Change ANY variable name to gcs_client for consistency
        # First, capture the original variable name BEFORE replacement
        client_var_match = re.search(r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"].*?\)', code, flags=re.DOTALL)
        original_client_var = client_var_match.group(1) if client_var_match else None
        
        # Track ALL variable mappings for comprehensive renaming
        if original_client_var and original_client_var != 'gcs_client':
            variable_mapping[original_client_var] = 'gcs_client'
        
        # Track common S3 variable patterns
        if 's3_client' in code and 's3_client' not in variable_mapping:
            variable_mapping['s3_client'] = 'gcs_client'
        
        if re.search(r'\bs3\b(?=\s*\.)', code) and 's3' not in variable_mapping:
            variable_mapping['s3'] = 'gcs_client'
        
        # Track other AWS-specific variable names
        if 's3_bucket' in code and 's3_bucket' not in variable_mapping:
            variable_mapping['s3_bucket'] = 'gcs_bucket'
        
        if 's3_key' in code and 's3_key' not in variable_mapping:
            variable_mapping['s3_key'] = 'blob_name'
        
        if 's3_object' in code and 's3_object' not in variable_mapping:
            variable_mapping['s3_object'] = 'blob'
        
        # Apply comprehensive variable renaming FIRST (before transformations)
        # This ensures all AWS variables are renamed to GCP-friendly names
        for old_var, new_var in variable_mapping.items():
            if old_var != new_var:
                # Use word boundaries to avoid partial matches
                # Protect comments and strings
                lines = code.split('\n')
                renamed_lines = []
                for line in lines:
                    # Skip comment lines
                    if line.strip().startswith('#'):
                        renamed_lines.append(line)
                        continue
                    # Replace variable name when followed by . or = or whitespace/end or (
                    # But not if it's part of a string literal
                    protected_line = line
                    # Replace variable name when followed by . or = or ( or whitespace/end
                    pattern = rf'\b{re.escape(old_var)}\b(?=\s*[.=\(\)\[\],:]|\s*$)'
                    protected_line = re.sub(pattern, new_var, protected_line)
                    renamed_lines.append(protected_line)
                code = '\n'.join(renamed_lines)
        
        # Replace client instantiation AFTER variable renaming
        # Handle boto3.client('s3') with optional region_name and config parameters
        # First, replace s3 = boto3.client('s3') -> gcs_client = storage.Client()
        # But only if gcs_client doesn't already exist AND the pattern still exists
        if re.search(r'\bs3\s*=\s*boto3\.client\([\'\"]s3[\'\"][^\)]*\)', code, flags=re.DOTALL):
            # Check if storage_client or gcs_client already exists - if so, just remove the boto3.client line
            if 'storage_client = storage.Client()' in code or 'gcs_client = storage.Client()' in code:
                # Remove the boto3.client line instead of replacing it
                # Match the entire line including the assignment
                lines = code.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Skip lines that match s3 = boto3.client('s3', ...)
                    if re.search(r'\bs3\s*=\s*boto3\.client\([\'\"]s3[\'\"][^\)]*\)', line, flags=re.DOTALL):
                        continue  # Skip this line
                    cleaned_lines.append(line)
                code = '\n'.join(cleaned_lines)
            else:
                code = re.sub(
                    r'\bs3\s*=\s*boto3\.client\([\'\"]s3[\'\"][^\)]*\)',
                    r'gcs_client = storage.Client()  # Use a better name for the GCS client',
                    code,
                    flags=re.DOTALL
                )
        # Then handle other variable names - but skip if storage_client or gcs_client already exists
        if 'storage_client = storage.Client()' not in code and 'gcs_client = storage.Client()' not in code:
            code = re.sub(
                r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"][^\)]*\)',
                r'\1 = storage.Client()',
                code,
                flags=re.DOTALL
            )
        
        # Replace boto3.resource('s3') if not already replaced - handle with region_name too
        # First, replace s3 = boto3.resource('s3') -> gcs_client = storage.Client()
        code = re.sub(
            r'\bs3\s*=\s*boto3\.resource\([\'\"]s3[\'\"][^\)]*\)',
            r'gcs_client = storage.Client()',
            code,
            flags=re.DOTALL
        )
        # Then handle other variable names
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.resource\([\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace S3 resource Bucket pattern: s3.Bucket('name')
        # But only if s3 is a storage.Client(), not if it's already gcs_client
        code = re.sub(
            r'(\w+)\.Bucket\(([^\)]+)\)',
            r'gcs_client.bucket(\2)',
            code
        )
        
        # Also handle: bucket = s3.Bucket('name') -> bucket = gcs_client.bucket('name')
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.Bucket\(([^\)]+)\)',
            r'\1 = gcs_client.bucket(\3)',
            code
        )
        
        # Also replace common S3 variable names (do this after specific replacement)
        code = re.sub(r'\bs3_client\b', 'gcs_client', code)
        # Replace standalone 's3' variable when used as a client (followed by dot)
        # Match: s3.upload_file, s3.put_object, etc. but not 's3' in strings
        # But be careful - only replace if it's clearly a client variable
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            # Skip if in string
            if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
                result_lines.append(line)
                continue
            # Replace s3 = storage.Client() -> gcs_client = storage.Client()
            line = re.sub(r'\bs3\s*=\s*storage\.Client\(\)', 'gcs_client = storage.Client()', line)
            # Replace s3 = ... (any assignment) -> gcs_client = ...
            if re.search(r'\bs3\s*=\s*', line):
                line = re.sub(r'\bs3\s*=\s*', 'gcs_client = ', line)
            # Replace s3. with gcs_client. (but not s3 = or s3=)
            if re.search(r'\bs3\s*\.', line) and not re.search(r'\bs3\s*=', line):
                line = re.sub(r'\bs3\s*\.', 'gcs_client.', line)
            # Replace standalone s3 variable (not in assignment) when followed by method call
            if re.search(r'\bs3\b', line) and not re.search(r'\bs3\s*=', line) and re.search(r'\bs3\s*\.', line):
                line = re.sub(r'\bs3\b(?=\s*\.)', 'gcs_client', line)
            result_lines.append(line)
        code = '\n'.join(result_lines)
        
        # Final pass: replace any remaining s3 variable references
        # But be careful not to replace 's3' in strings
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            # Skip if in string
            if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
                result_lines.append(line)
                continue
            # Replace s3 = storage.Client() if still present
            line = re.sub(r'\bs3\s*=\s*storage\.Client\(\)', 'gcs_client = storage.Client()', line)
            # Replace s3. method calls
            line = re.sub(r'\bs3\s*\.', 'gcs_client.', line)
            result_lines.append(line)
        code = '\n'.join(result_lines)
        
        # Also handle cases where 's3' might be used without dot (less common but possible)
        # But be careful - only replace if it's clearly a variable reference
        # This is a fallback for edge cases
        
        # Add variable definitions after client initialization
        # Find where to insert (after gcs_client line)
        if 'gcs_client = storage.Client()' in code:
            # Insert variable definitions after client
            var_defs = f'\nbucket_name = "{bucket_name}"\nremote_file_name = "{remote_file_name}"\nlocal_upload_file = "{local_upload_file}"\nlocal_download_file = "{local_download_file}"'
            # Replace the client line, preserving any existing comment format
            code = re.sub(
                r'gcs_client = storage\.Client\(\)\s*# Use a better name for the GCS client',
                f'gcs_client = storage.Client()  # Use a better name for the GCS client{var_defs}',
                code
            )
        
        # Replace S3 upload_file -> GCS upload_from_filename with improved structure
        # Pattern: s3_client.upload_file('local_file.txt', 'bucket-name', 'remote_file.txt')
        # Should become: storage_client = storage.Client(); bucket = storage_client.bucket('bucket-name'); blob = bucket.blob('remote_file.txt'); blob.upload_from_filename('local_file.txt')
        def replace_upload(match):
            client_var = match.group(1)  # Could be 's3', 'gcs_client', etc.
            local_file = match.group(2)
            bucket_name_var = match.group(3)
            remote_file = match.group(4)
            # Correct GCS API pattern
            return f'storage_client = storage.Client()\nbucket = storage_client.bucket({bucket_name_var})\nblob = bucket.blob({remote_file})\nblob.upload_from_filename({local_file})\nprint(f"File \'{local_file}\' uploaded to \'{bucket_name_var}/{remote_file}\' successfully.")'
        code = re.sub(
            r'(\w+)\.upload_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)',
            replace_upload,
            code
        )
        
        # Replace S3 download_file -> GCS download_to_filename with improved structure
        # Pattern: s3_client.download_file('bucket-name', 'remote_file.txt', 'local_file.txt')
        # Should become: storage_client = storage.Client(); bucket = storage_client.bucket('bucket-name'); blob = bucket.blob('remote_file.txt'); blob.download_to_filename('local_file.txt')
        def replace_download(match):
            client_var = match.group(1)
            bucket_name_var = match.group(2)
            remote_file = match.group(3)
            local_file = match.group(4)
            # Correct GCS API pattern
            return f'storage_client = storage.Client()\nbucket = storage_client.bucket({bucket_name_var})\nblob = bucket.blob({remote_file})\nblob.download_to_filename({local_file})\nprint(f"File \'{remote_file}\' downloaded from \'{bucket_name_var}\' to \'{local_file}\' successfully.")'
        code = re.sub(
            r'(\w+)\.download_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)',
            replace_download,
            code
        )
        
        # Replace S3 put_object -> GCS upload with improved structure
        # This should happen AFTER client variable replacement
        def replace_put_object(match):
            # Client var should already be gcs_client at this point
            body_expr = match.group(4)
            return f'### 🚀 Upload file to GCS\nbucket = gcs_client.bucket(bucket_name)\nblob = bucket.blob(remote_file_name)\nblob.upload_from_string({body_expr})\nprint(f"File uploaded to gs://{{bucket_name}}/{{remote_file_name}}")'
        # Match put_object with proper handling of closing paren
        code = re.sub(
            r'(\w+)\.put_object\(Bucket=([^,]+),\s*Key=([^,]+),\s*Body=([^\)]+)\)',
            replace_put_object,
            code
        )
        
        # Replace S3 get_object -> GCS download with improved structure
        # Handle both: s3.get_object(...) and response = s3.get_object(...)
        def replace_get_object(match):
            # Extract bucket and key from the match
            bucket_expr = match.group(3) if len(match.groups()) >= 3 else 'bucket_name'
            key_expr = match.group(4) if len(match.groups()) >= 4 else 'object_key'
            # Clean up expressions (remove quotes if present)
            bucket_expr = bucket_expr.strip().strip('\'"')
            key_expr = key_expr.strip().strip('\'"')
            return f'bucket = storage_client.bucket({bucket_expr})\nblob = bucket.blob({key_expr})\ncsv_content = blob.download_as_text()'
        
        # Match get_object with optional additional parameters
        # Pattern: response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)[^\)]*\)',
            replace_get_object,
            code
        )
        code = re.sub(
            r'(\w+)\.get_object\(Bucket=([^,]+),\s*Key=([^,\)]+)[^\)]*\)',
            replace_get_object,
            code
        )
        
        # Handle response['Body'].read().decode('utf-8') pattern - replace with csv_content
        # This should happen after get_object transformation
        code = re.sub(
            r'(\w+)\[\'Body\'\]\.read\(\)\.decode\([\'"]utf-8[\'"]\)',
            r'csv_content',
            code
        )
        code = re.sub(
            r'(\w+)\["Body"\]\.read\(\)\.decode\([\'"]utf-8[\'"]\)',
            r'csv_content',
            code
        )
        code = re.sub(
            r'(\w+)\[\'Body\'\]\.read\(\)',
            r'csv_content',
            code
        )
        code = re.sub(
            r'(\w+)\["Body"\]\.read\(\)',
            r'csv_content',
            code
        )
        
        # Replace S3 delete_object -> GCS delete with improved structure
        def replace_delete_object(match):
            bucket_name_var = match.group(2).strip('\'"') if len(match.groups()) >= 2 else 'bucket_name'
            key_var = match.group(3).strip('\'"') if len(match.groups()) >= 3 else 'remote_file_name'
            # Correct GCS API pattern
            return f'storage_client = storage.Client()\nbucket = storage_client.bucket("{bucket_name_var}")\nblob = bucket.blob("{key_var}")\nblob.delete()\nprint(f"Object \'{key_var}\' deleted from bucket \'{bucket_name_var}\' successfully.")'
        code = re.sub(
            r'(\w+)\.delete_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            replace_delete_object,
            code
        )
        
        # Replace S3 list_objects_v2 -> GCS list_blobs with improved structure
        # Pattern: response = s3_client.list_objects_v2(Bucket='my-bucket')
        # Should become: storage_client = storage.Client(); blobs = storage_client.list_blobs(bucket_name)
        def replace_list_objects_v2(match):
            # Correct GCS API pattern
            return f'storage_client = storage.Client()\nblobs = storage_client.list_blobs(bucket_name)\nprint(f"Contents of bucket \'{{bucket_name}}\':")\nfor blob in blobs:\n    print(f"- {{blob.name}}")'
        
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.list_objects_v2\(Bucket=([^,\)]+)\)',
            replace_list_objects_v2,
            code
        )
        code = re.sub(
            r'(\w+)\.list_objects_v2\(Bucket=([^,\)]+)\)',
            replace_list_objects_v2,
            code
        )
        
        # Replace S3 list_objects -> GCS list_blobs
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.list_objects\(Bucket=([^,\)]+)\)',
            replace_list_objects_v2,
            code
        )
        code = re.sub(
            r'(\w+)\.list_objects\(Bucket=([^,\)]+)\)',
            replace_list_objects_v2,
            code
        )
        
        # Replace botocore.config import and usage
        code = re.sub(r'from botocore\.config import Config', '', code)
        code = re.sub(r'import botocore\.config', '', code)
        code = re.sub(r'from botocore import config', '', code)
        # Remove config parameter from boto3.client calls - handle multiline
        # Handle: boto3.client('s3', config=Config(...)) - must match BEFORE variable assignment
        code = re.sub(r'boto3\.client\s*\(\s*[\'\"]s3[\'\"],\s*config\s*=\s*Config\([^)]+\)\s*\)', 'storage.Client()', code, flags=re.DOTALL)
        # Handle: s3_client = boto3.client('s3', config=Config(...))
        code = re.sub(r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]s3[\'\"],\s*config\s*=\s*Config\([^)]+\)\s*\)', r'\1 = storage.Client()', code, flags=re.DOTALL)
        # Remove config parameter from boto3.client calls - handle multiline (fallback)
        code = re.sub(r',\s*config\s*=\s*Config\([^)]+\)', '', code, flags=re.DOTALL)
        code = re.sub(r'config\s*=\s*Config\([^)]+\),\s*', '', code, flags=re.DOTALL)
        code = re.sub(r'config\s*=\s*Config\([^)]+\)', '', code, flags=re.DOTALL)
        
        # Replace S3 generate_presigned_url -> GCS signed URL
        # Pattern: url = s3_client.generate_presigned_url('get_object', Params={'Bucket': 'my-bucket', 'Key': 'file.txt'}, ExpiresIn=3600)
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.generate_presigned_url\([\'"]get_object[\'"],\s*Params=\{[\'"]Bucket[\'"]:\s*([^,]+),\s*[\'"]Key[\'"]:\s*([^}]+)\},\s*ExpiresIn=([^\)]+)\)',
            r'from datetime import datetime, timedelta\nbucket = gcs_client.bucket(\3)\nblob = bucket.blob(\4)\n\1 = blob.generate_signed_url(expiration=datetime.utcnow() + timedelta(seconds=\5), method="GET")',
            code
        )
        code = re.sub(
            r'(\w+)\.generate_presigned_url\([\'"]get_object[\'"],\s*Params=\{[\'"]Bucket[\'"]:\s*([^,]+),\s*[\'"]Key[\'"]:\s*([^}]+)\},\s*ExpiresIn=([^\)]+)\)',
            r'from datetime import datetime, timedelta\nbucket = gcs_client.bucket(\2)\nblob = bucket.blob(\3)\nurl = blob.generate_signed_url(expiration=datetime.utcnow() + timedelta(seconds=\4), method="GET")',
            code
        )
        
        # Replace S3 create_multipart_upload -> GCS (not directly supported, use resumable upload)
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.create_multipart_upload\(Bucket=([^,]+),\s*Key=([^\)]+)\)',
            r'# GCS uses resumable uploads instead of multipart\n# Use blob.upload_from_filename() for large files - it handles resumable uploads automatically\nbucket = gcs_client.bucket(\3)\nblob = bucket.blob(\4)\n# For resumable upload: blob.upload_from_filename("file.zip", resumable=True)',
            code
        )
        code = re.sub(
            r'(\w+)\.create_multipart_upload\(Bucket=([^,]+),\s*Key=([^\)]+)\)',
            r'# GCS uses resumable uploads instead of multipart\n# Use blob.upload_from_filename() for large files - it handles resumable uploads automatically\nbucket = gcs_client.bucket(\2)\nblob = bucket.blob(\3)\n# For resumable upload: blob.upload_from_filename("file.zip", resumable=True)',
            code
        )
        
        # Replace S3 list_object_versions -> GCS versioning
        # Pattern: versions = s3.list_object_versions(Bucket='my-bucket', Prefix='file.txt')
        code = re.sub(
            r'(\w+)\s*=\s*(\w+)\.list_object_versions\(Bucket=([^,]+),\s*Prefix=([^\)]+)\)',
            r'bucket = gcs_client.bucket(\3)\nblobs = bucket.list_blobs(prefix=\4, versions=True)\n\1 = [{"VersionId": blob.generation, "Name": blob.name} for blob in blobs]',
            code
        )
        code = re.sub(
            r'(\w+)\.list_object_versions\(Bucket=([^,]+),\s*Prefix=([^\)]+)\)',
            r'bucket = gcs_client.bucket(\2)\nblobs = bucket.list_blobs(prefix=\3, versions=True)\nversions = [{"VersionId": blob.generation, "Name": blob.name} for blob in blobs]',
            code
        )
        
        # Handle versions.get('Versions', []) pattern
        code = re.sub(
            r'versions\.get\([\'"]Versions[\'"],\s*\[\]\)',
            r'versions',
            code
        )
        
        # Handle version['VersionId'] pattern
        code = re.sub(
            r'version\[[\'"]VersionId[\'"]\]',
            r'version["VersionId"]',
            code
        )
        
        # Fix loops that use response.get('Contents', []) pattern
        # Pattern: for obj in response.get('Contents', []): print(obj['Key'])
        # Should become: for blob in blobs: print(blob.name)
        code = re.sub(
            r'for\s+obj\s+in\s+(\w+)\.get\([\'"]Contents[\'"],\s*\[\]\):',
            r'for blob in blobs:\n    # Use blob.name to get the object key/path',
            code
        )
        code = re.sub(
            r'for\s+(\w+)\s+in\s+(\w+)\.get\([\'"]Contents[\'"],\s*\[\]\):',
            r'for blob in blobs:\n    # Use blob.name to get the object key/path',
            code
        )
        # Replace obj['Key'] with blob.name (obj variable becomes blob)
        # Track this variable change
        if re.search(r'\bobj\b', code) and 'obj' not in variable_mapping:
            variable_mapping['obj'] = 'blob'
        
        code = re.sub(r"obj\['Key'\]", r'blob.name', code)
        code = re.sub(r'obj\["Key"\]', r'blob.name', code)
        # Also handle any other obj references in the loop context
        code = re.sub(r'\bobj\b', 'blob', code)  # Replace obj with blob in loop context
        
        # Track response variable changes for list operations BEFORE transformation
        # Find response variables from list_objects operations in ORIGINAL code
        # We need to do this before the transformation changes the code structure
        # So we'll track it earlier, but apply renaming after we've identified all variables
        
        # Remove ALL AWS/S3 references from comments and replace with GCP comments
        code = re.sub(r'#\s*AWS\s+S3\s+example', '# 🌟 GCP Cloud Storage Example', code, flags=re.IGNORECASE)
        code = re.sub(r'#\s*Upload\s+file\s+to\s+S3', '', code, flags=re.IGNORECASE)
        code = re.sub(r'#\s*Download\s+file\s+from\s+S3', '', code, flags=re.IGNORECASE)
        code = re.sub(r'#\s*List\s+objects\s+in\s+bucket', '', code, flags=re.IGNORECASE)
        code = re.sub(r'#\s*AWS.*?S3.*?', '', code, flags=re.IGNORECASE)
        # Remove any remaining S3 references in comments
        code = re.sub(r'#.*?S3.*?', '', code, flags=re.IGNORECASE)
        code = re.sub(r'#.*?s3.*?', '', code, flags=re.IGNORECASE)
        # Remove AWS region comments that mention S3
        code = re.sub(r'#.*?AWS.*?region.*?S3.*?', '', code, flags=re.IGNORECASE)
        
        # Clean up multiple blank lines
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        # Add header comment if not present
        if '# 🌟 GCP Cloud Storage Example' not in code:
            # Insert after import if it's the first line
            if code.startswith('from google.cloud import storage'):
                code = code.replace('from google.cloud import storage',
                                  'from google.cloud import storage\n\n# 🌟 GCP Cloud Storage Example', 1)
            else:
                # Find import line and add after it
                code = re.sub(r'(from google\.cloud import storage)',
                            r'\1\n\n# 🌟 GCP Cloud Storage Example',
                            code,
                            count=1)
        
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
        
        # Replace S3 create_bucket -> GCS bucket.create() (second pass - handles any remaining after variable renaming)
        # This handles cases where create_bucket wasn't caught in the first pass
        def replace_create_bucket_late(match):
            full_match = match.group(0)
            bucket_name_expr = match.group(2).strip().strip('\'"')
            
            location = None
            location_config_match = re.search(r'CreateBucketConfiguration\s*=\s*\{[^}]*LocationConstraint[^}]*:\s*[\'"]([^\'"]+)[\'"]', full_match)
            if location_config_match:
                aws_region = location_config_match.group(1)
                location = self._map_aws_region_to_gcp_location(aws_region)
            
            if location is None:
                region_match = re.search(r'region\s*=\s*[\'"]([^\'"]+)[\'"]', code)
                if region_match:
                    aws_region = region_match.group(1)
                    location = self._map_aws_region_to_gcp_location(aws_region)
            
            bucket_name_str = f"'{bucket_name_expr}'" if not bucket_name_expr.startswith("'") and not bucket_name_expr.startswith('"') else bucket_name_expr
            
            if location:
                # Correct GCS API: storage_client.create_bucket(bucket_name, location=location)
                return f'storage_client = storage.Client()\nbucket = storage_client.create_bucket({bucket_name_str}, location=\'{location}\')\nprint(f"Bucket \'{{bucket.name}}\' created successfully in location \'{location}\'.")'
            else:
                # Default location is 'US' for GCS
                return f'storage_client = storage.Client()\nbucket = storage_client.create_bucket({bucket_name_str})\nprint(f"Bucket \'{{bucket.name}}\' created successfully.")'
        
        # Match create_bucket with Bucket parameter (second pass - after variable renaming)
        code = re.sub(
            r'(\w+)\.create_bucket\(\s*Bucket\s*=\s*([^,]+)(?:,\s*CreateBucketConfiguration\s*=\s*\{[^}]+\})?\s*\)',
            replace_create_bucket_late,
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\.create_bucket\(\s*([^,\)]+)\s*\)',
            replace_create_bucket_late,
            code
        )
        
        # Replace S3 delete_bucket -> GCS delete_bucket with improved structure
        def replace_delete_bucket(match):
            bucket_name_var = match.group(2).strip('\'"') if len(match.groups()) >= 2 else 'bucket_name'
            # Correct GCS API pattern: storage_client.get_bucket(bucket_name).delete()
            return f'storage_client = storage.Client()\nstorage_client.get_bucket("{bucket_name_var}").delete()\nprint(f"Bucket \'{bucket_name_var}\' deleted successfully.")'
        code = re.sub(
            r'(\w+)\.delete_bucket\(Bucket=([^,\)]+)\)',
            replace_delete_bucket,
            code
        )
        
        # Remove or comment AWS region names
        # Replace AWS region constants/variables
        # BUT: Don't modify function parameter defaults - only modify variable assignments
        aws_regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
            'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2',
            'ap-south-1', 'sa-east-1', 'ca-central-1'
        ]
        for region in aws_regions:
            # Comment out region assignments (but NOT function parameter defaults)
            # Only match variable assignments, not function parameters
            code = re.sub(
                rf'^(\s+)(\w+)\s*=\s*[\'"]{region}[\'"]',
                rf'\1# \2 = \'{region}\'  # Region not needed for GCP (uses GCP_REGION env var)',
                code,
                flags=re.MULTILINE
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
        # Handle region_name in various positions - be more aggressive
        # First handle region_name with quotes - match more patterns
        code = re.sub(
            r',\s*region_name\s*=\s*[\'"][^\'"]+[\'"]',
            '',
            code
        )
        code = re.sub(
            r'region_name\s*=\s*[\'"][^\'"]+[\'"]\s*,',
            '',
            code
        )
        code = re.sub(
            r'region_name\s*=\s*[\'"][^\'"]+[\'"]',
            '',
            code
        )
        # Then handle region_name without quotes
        code = re.sub(
            r',\s*region_name\s*=\s*[^\s,\)]+',
            '',
            code
        )
        code = re.sub(
            r'region_name\s*=\s*[^\s,\)]+\s*,',
            '',
            code
        )
        code = re.sub(
            r'region_name\s*=\s*[^\s,\)]+',
            '',
            code
        )
        
        # Also handle region_name in boto3.client/resource calls specifically
        # Match: boto3.client('s3', region_name='us-west-2')
        code = re.sub(
            r'boto3\.(client|resource)\s*\(\s*([^,]+),\s*region_name\s*=\s*[^\)]+\)',
            r'boto3.\1(\2)',
            code
        )
        # Match: boto3.client('s3', region_name='us-west-2', ...)
        code = re.sub(
            r'boto3\.(client|resource)\s*\(\s*([^,]+),\s*region_name\s*=\s*[^,]+\s*,\s*([^\)]+)\)',
            r'boto3.\1(\2, \3)',
            code
        )
        # Match: s3_client = boto3.client('s3', region_name='us-west-2')
        # This should remove region_name and then the final pass will replace boto3.client
        # Handle with quotes: region_name='value' or region_name="value"
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.(client|resource)\s*\(\s*([^,]+),\s*region_name\s*=\s*[\'"][^\'"]+[\'"]\s*\)',
            r'\1 = boto3.\2(\3)',
            code
        )
        # Match: dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.(client|resource)\s*\(\s*[\'"](\w+)[\'"],\s*region_name\s*=\s*[\'"]([^\'"]+)[\'"]\s*\)',
            r'\1 = boto3.\2(\'\3\')',
            code
        )
        # Also handle without quotes (variable): region_name=var_name
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.(client|resource)\s*\(\s*([^,]+),\s*region_name\s*=\s*[^,\)]+\s*\)',
            r'\1 = boto3.\2(\3)',
            code
        )
        
        # After removing region_name, replace boto3.client/resource calls
        # This ensures we catch cases where region_name was removed but boto3 call remains
        # Handle all services, not just S3
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.resource\s*\(\s*[\'\"]s3[\'\"][^\)]*\)',
            r'\1 = storage.Client()',
            code,
            flags=re.DOTALL
        )
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.resource\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        # Ensure imports are present for DynamoDB if needed
        if 'firestore.Client()' in code and 'from google.cloud import firestore' not in code:
            # Insert after storage import if present
            if 'from google.cloud import storage' in code:
                code = code.replace('from google.cloud import storage', 'from google.cloud import storage\nfrom google.cloud import firestore', 1)
            else:
                code = 'from google.cloud import firestore\n' + code
        
        # Clean up any double commas or trailing commas
        code = re.sub(r',\s*,', ',', code)
        code = re.sub(r'\(\s*,', '(', code)
        code = re.sub(r',\s*\)', ')', code)
        # Clean up empty function calls
        code = re.sub(r'\(\s*\)', '()', code)
        # Clean up spaces before closing paren
        code = re.sub(r'\s+\)', ')', code)
        
        # Final pass: If gcs_client exists but storage_client is referenced, replace storage_client with gcs_client
        # This ensures consistency when gcs_client was created by boto3.client replacement
        if 'gcs_client = storage.Client()' in code:
            # Replace storage_client method calls with gcs_client
            code = code.replace('storage_client.create_bucket', 'gcs_client.create_bucket')
            code = code.replace('storage_client.bucket', 'gcs_client.bucket')
            code = code.replace('storage_client.list_blobs', 'gcs_client.list_blobs')
            code = code.replace('storage_client.get_bucket', 'gcs_client.get_bucket')
            code = code.replace('storage_client.list_buckets', 'gcs_client.list_buckets')
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)
        
        return code, variable_mapping
    
    def _validate_and_fix_with_gemini(self, refactored_code: str, original_code: str) -> str:
        """Use Gemini API to validate refactored code and fix any remaining AWS patterns.
        
        This ensures the refactored code is correct for Google Cloud Platform and
        doesn't mix AWS and GCP APIs.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            import google.generativeai as genai
            from config import Config
            
            if not Config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not set, skipping Gemini validation")
                return refactored_code
            
            genai.configure(api_key=Config.GEMINI_API_KEY)
            # Use correct model names with models/ prefix
            # Try gemini-2.5-flash (fastest), then gemini-2.5-pro (better quality)
            try:
                model = genai.GenerativeModel('models/gemini-2.5-flash')
            except Exception:
                try:
                    model = genai.GenerativeModel('models/gemini-2.5-pro')
                except Exception:
                    # Fallback to older models
                    try:
                        model = genai.GenerativeModel('models/gemini-pro')
                    except Exception:
                        model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            # Check if code still has AWS patterns - be comprehensive
            aws_patterns = [
                'boto3', 'botocore', 's3.buckets', 's3.meta.client', 
                's3.Bucket', 's3.create_bucket', 's3.upload_file',
                's3.download_file', 's3.list_objects', 'ResponseMetadata',
                'LocationConstraint', 'ACL', 'CreateBucketConfiguration',
                'self.s3', 's3_client', 's3_bucket', 's3_key', 's3_object',
                'Bucket=', 'Key=', 'QueueUrl=', 'TopicArn=', 'TableName=',
                'FunctionName=', 'InvocationType=', 'Payload=', 'Region=',
                'aws_access_key', 'aws_secret', 'AWS_ACCESS_KEY', 'AWS_SECRET',
                'amazonaws.com', '.s3.', 's3://', 'S3Manager', 'S3Client',
                'dynamodb_client', 'sqs_client', 'sns_client', 'lambda_handler',
                'DYNAMODB_TABLE_NAME', 'SQS_DLQ_URL', 'SNS_TOPIC_ARN',
                'event[\'Records\']', 'event["Records"]', 'record_event[\'s3\']',
                'record_event["s3"]', 'get_object', 'batch_write_item',
                'send_message', 'QueueUrl', 'TopicArn', 'RequestItems',
                'PutRequest', 'Item=', 'MessageBody=', 'Message='
            ]
            
            # Check for patterns (case-insensitive for some)
            has_aws_patterns = False
            refactored_lower = refactored_code.lower()
            for pattern in aws_patterns:
                if pattern.lower() in refactored_lower or pattern in refactored_code:
                    has_aws_patterns = True
                    break
            
            # Also check for common AWS method patterns
            aws_method_patterns = [
                r'\bboto3\s*\.\s*(client|resource)\s*\(',
                r'\bs3\s*\.\s*\w+',  # s3.something
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
            
            if not has_aws_patterns:
                for pattern in aws_method_patterns:
                    if re.search(pattern, refactored_code, re.IGNORECASE):
                        has_aws_patterns = True
                        break
            
            # ALWAYS run Gemini validation if there are ANY AWS patterns detected
            # This ensures we catch everything, even if regex missed something
            if not has_aws_patterns:
                # Double-check with more aggressive patterns
                aggressive_patterns = [
                    r'boto3',
                    r'\.get_object\s*\(',
                    r'\.batch_write_item\s*\(',
                    r'\.send_message\s*\(',
                    r'Bucket\s*=',
                    r'Key\s*=',
                    r'QueueUrl\s*=',
                    r'TopicArn\s*=',
                    r'RequestItems\s*=',
                    r'DYNAMODB',
                    r'SQS_',
                    r'SNS_',
                    r'lambda_handler',
                ]
                for pattern in aggressive_patterns:
                    if re.search(pattern, refactored_code, re.IGNORECASE):
                        has_aws_patterns = True
                        break
            
            # ALWAYS validate with Gemini for multi-service code (Lambda with S3/DynamoDB/SQS/SNS)
            # Check if this is multi-service code
            is_multi_service = (
                re.search(r'\blambda_handler\s*\(', refactored_code, re.IGNORECASE) or
                re.search(r'\bprocess_gcs_file\s*\(', refactored_code, re.IGNORECASE) or
                re.search(r'event\s*\[\s*[\'"]Records[\'"]\s*\]', refactored_code) or
                (re.search(r'\b(get_object|batch_write|send_message|publish)\s*\(', refactored_code) and
                 re.search(r'\b(storage|firestore|pubsub)\b', refactored_code))
            )
            
            # ALWAYS run Gemini validation if:
            # 1. AWS patterns detected, OR
            # 2. Multi-service code (Lambda with multiple services), OR
            # 3. Any suspicious AWS-like patterns
            if not has_aws_patterns and not is_multi_service:
                # Final check - only skip if we're 100% certain there are no AWS patterns
                if not re.search(r'\b(boto3|dynamodb|sqs|sns|lambda_handler|get_object|batch_write|send_message|QueueUrl|TopicArn|s3_client|dynamodb_client|sqs_client|sns_client)\b', refactored_code, re.IGNORECASE):
                    # No AWS patterns found, return as-is
                    return refactored_code
            
            # Use Gemini to fix the code - handle multi-service Lambda code
            prompt = f"""You are a code refactoring expert. The following Python code was supposed to be refactored from AWS Lambda (with S3, DynamoDB, SQS, SNS) to Google Cloud Platform, but it still contains AWS patterns mixed with GCP code.

**CRITICAL REQUIREMENTS - ZERO TOLERANCE FOR AWS CODE:**

1. **Lambda Handler Conversion (MANDATORY):**
   - `def lambda_handler(event, context):` → `def process_gcs_file(data, context):` (for GCS-triggered)
   - Remove `event['Records']` loop completely - GCS background functions receive single file events
   - Replace `event['Records'][0]['s3']['bucket']['name']` → `data.get('bucket')`
   - Replace `event['Records'][0]['s3']['object']['key']` → `data.get('name')`
   - Replace `for record_event in event['Records']:` → Remove loop, process single file directly
   - Replace `if not event.get('Records'):` → `if not data.get('bucket') or not data.get('name'):`
   - Replace `if 's3' not in record_event:` → Remove this check (GCS events don't have 's3' key)
   - Replace ALL references to `event` variable → `data` variable
   - Remove AWS Lambda response format: `return {{'statusCode': 200, 'body': ...}}` → Just `return` or raise exceptions
   - Cloud Functions don't return HTTP status codes - they raise exceptions for errors

2. **S3 to GCS Conversion (MANDATORY):**
   - Remove ALL `boto3.client('s3')` and `boto3.resource('s3')` initialization
   - Replace `s3_client = storage.Client()` → `storage_client = storage.Client()` (rename variable)
   - Replace `s3_client.get_object(Bucket=bucket_name, Key=object_key)` → `bucket = storage_client.bucket(bucket_name); blob = bucket.blob(object_key); csv_content = blob.download_as_text()`
   - Replace `response = s3_client.get_object(...)` → Use bucket.blob pattern above
   - Replace `response['Body'].read().decode('utf-8')` → `blob.download_as_text()`
   - Replace ALL `s3_client.` method calls → Use `storage_client.bucket().blob()` pattern
   - Replace `s3://` URLs → `gs://` URLs in print statements and comments
   - Replace `storage_client.exceptions.NoSuchKey` → `from google.cloud.exceptions import NotFound` and catch `NotFound`
   - Use `from google.cloud import storage` and `storage_client = storage.Client()`
   - Remove redundant assignments like `csv_content = csv_content`

3. **DynamoDB to Firestore Conversion (MANDATORY):**
   - Remove ALL `boto3.client('dynamodb')` initialization
   - Replace `dynamodb_client = boto3.client('dynamodb')` → `firestore_db = firestore.Client()`
   - Replace function names: `batch_write_to_dynamodb` → `batch_write_to_firestore`
   - Replace `dynamodb_client.batch_write_item(RequestItems={{TABLE: batch}})` → `batch = firestore_db.batch(); collection_ref = firestore_db.collection(collection_name); for item in items: doc_ref = collection_ref.document(); batch.set(doc_ref, item); batch.commit()`
   - DO NOT create broken code like `response = batch = firestore_db.batch()` - fix this properly
   - DO NOT use invalid syntax like `FIRESTORE_COLLECTION_NAME: batch` - use proper collection reference
   - Replace DynamoDB item format `{{'S': 'value'}}` → native Python dicts (just `'value'`)
   - Replace `{{'N': '123'}}` → `123` (integer)
   - Remove DynamoDB-specific logic: batch size 25, UnprocessedItems checking - Firestore uses batch size 500
   - Use `from google.cloud import firestore` and `firestore_db = firestore.Client()`

4. **SQS to Pub/Sub Conversion (MANDATORY):**
   - Remove ALL `boto3.client('sqs')` initialization
   - Replace `sqs_client = boto3.client('sqs')` → `pubsub_publisher = pubsub_v1.PublisherClient()`
   - Replace function names: `send_to_dlq` → `publish_error_message`
   - Replace `sqs_client.send_message(QueueUrl=url, MessageBody=body)` → `import os; topic_path = pubsub_publisher.topic_path(os.getenv('GCP_PROJECT_ID'), os.getenv('GCP_PUBSUB_TOPIC_ID')); future = pubsub_publisher.publish(topic_path, json.dumps(body).encode('utf-8')); future.result()`
   - Remove `QueueUrl` parameter completely - use `topic_path` instead
   - Replace `SQS_DLQ_URL` env var → `PUB_SUB_ERROR_TOPIC` (full path format: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
   - Use `from google.cloud import pubsub_v1` and `pubsub_publisher = pubsub_v1.PublisherClient()`
   - Remove duplicate client initialization - only initialize once

5. **SNS to Pub/Sub Conversion (MANDATORY):**
   - Remove ALL `boto3.client('sns')` initialization
   - Replace `sns_client = boto3.client('sns')` → `pubsub_publisher = pubsub_v1.PublisherClient()` (can reuse same publisher)
   - Replace function names: `publish_sns_summary` → `publish_summary_message`
   - Replace `sns_client.publish(TopicArn=arn, Message=msg, Subject=subj)` → `import os; topic_path = pubsub_publisher.topic_path(os.getenv('GCP_PROJECT_ID'), os.getenv('GCP_PUBSUB_TOPIC_ID')); future = pubsub_publisher.publish(topic_path, msg.encode('utf-8')); future.result()`
   - REMOVE `Subject=` parameter - Pub/Sub doesn't support it, use message attributes if needed
   - Use the global `PUB_SUB_SUMMARY_TOPIC` environment variable, don't hardcode topic paths
   - Replace `SNS_TOPIC_ARN` env var → `PUB_SUB_SUMMARY_TOPIC` (full path format: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
   - Use Pub/Sub topics instead of SNS topics

6. **Environment Variables (MANDATORY):**
   - Replace `DYNAMODB_TABLE_NAME` → `FIRESTORE_COLLECTION_NAME`
   - Replace `SQS_DLQ_URL` → `PUB_SUB_ERROR_TOPIC` (full path: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
   - Replace `SNS_TOPIC_ARN` → `PUB_SUB_SUMMARY_TOPIC` (full path: `projects/{{PROJECT_ID}}/topics/{{TOPIC_NAME}}`)
   - Default values must be GCP format, NOT AWS URLs/ARNs
   - Remove comments mentioning "Lambda configuration" - use "Cloud Function configuration"

7. **Exception Handling (MANDATORY):**
   - Replace `s3_client.exceptions.NoSuchKey` → `from google.cloud.exceptions import NotFound` and catch `NotFound`
   - Replace `storage_client.exceptions.NoSuchKey` → `from google.cloud.exceptions import NotFound` and catch `NotFound`
   - Remove all `botocore` exception imports
   - Remove all `boto3` imports

8. **Variable Naming (MANDATORY):**
   - Replace `s3_client` → `storage_client`
   - Replace `dynamodb_client` → `firestore_db`
   - Replace `sqs_client` → `pubsub_publisher`
   - Replace `sns_client` → `pubsub_publisher`
   - Replace dictionary keys: `'s3_key'` → `'object_key'` or `'gcs_file'`

9. **Syntax Fixes (MANDATORY):**
   - Fix comment syntax: If a line starts with `#` but the next line is code, ensure proper comment formatting
   - Remove redundant assignments: `csv_content = csv_content` → Remove
   - Remove duplicate client initializations: Only initialize each client once
   - Fix broken Pub/Sub syntax: `future = pubsub_publisher.publish(...))` → `future = pubsub_publisher.publish(...)`
   - Fix broken batch syntax: `response = batch = firestore_db.batch()` → `batch = firestore_db.batch()`
   - Fix invalid collection path: `FIRESTORE_COLLECTION_NAME: batch` → `collection_ref = firestore_db.collection(FIRESTORE_COLLECTION_NAME)`

10. **Return Format (MANDATORY):**
    - Remove AWS Lambda response format: `return {{'statusCode': 200, 'body': '...'}}`
    - Cloud Functions return None or raise exceptions - no status codes
    - Replace with: `return` or `raise Exception(...)`

11. **Return ONLY the corrected Python code, NO explanations, NO markdown, just pure Python code**

**Original AWS Code (for reference):**
```python
{original_code[:3000]}  # First 3000 chars for context
```

**Incorrectly Refactored Code (needs fixing - contains AWS patterns):**
```python
{refactored_code}
```

**Corrected Google Cloud Platform Code (pure Python, no AWS code):**"""
            
            # Add timeout handling for Gemini validation
            import threading
            
            response_result = [None]
            exception_result = [None]
            
            def generate_with_timeout():
                try:
                    import google.generativeai.types as genai_types
                    generation_config = genai_types.GenerationConfig(
                        max_output_tokens=8192,
                        temperature=0.1,
                    )
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
                logger.warning("Gemini validation call timed out after 90 seconds")
                return refactored_code  # Return original if timeout
            
            if exception_result[0]:
                logger.warning(f"Gemini validation error: {exception_result[0]}")
                return refactored_code
            
            if not response_result[0]:
                logger.warning("No response from Gemini validation")
                return refactored_code
            
            response = response_result[0]
            corrected_code = response.text.strip()
            
            # Extract code from markdown code blocks if present - be more aggressive
            # Try multiple extraction patterns
            if '```python' in corrected_code:
                parts = corrected_code.split('```python')
                if len(parts) > 1:
                    corrected_code = parts[1].split('```')[0].strip()
            elif '```' in corrected_code:
                parts = corrected_code.split('```')
                # Find the largest code block (usually the actual code)
                code_blocks = []
                for i in range(1, len(parts), 2):
                    if i < len(parts):
                        block = parts[i].strip()
                        if block and len(block) > 50:  # Reasonable code block size
                            code_blocks.append(block)
                if code_blocks:
                    # Use the largest code block
                    corrected_code = max(code_blocks, key=len)
            
            # Remove any leading/trailing markdown or explanations
            # Remove lines that start with "Here's" or "Here is" or similar explanations
            lines = corrected_code.split('\n')
            cleaned_lines = []
            code_started = False
            for line in lines:
                stripped = line.strip()
                # Skip explanation lines at the start
                if not code_started:
                    if stripped.startswith('Here') or stripped.startswith('The') or stripped.startswith('This'):
                        continue
                    if stripped.startswith('import') or stripped.startswith('from') or stripped.startswith('def'):
                        code_started = True
                
                if code_started or stripped:
                    cleaned_lines.append(line)
            
            corrected_code = '\n'.join(cleaned_lines).strip()
            
            # Final cleanup: remove any remaining markdown or explanation text
            # Remove lines that are clearly explanations (not code)
            lines = corrected_code.split('\n')
            final_lines = []
            for line in lines:
                stripped = line.strip()
                # Skip lines that are clearly explanations
                if stripped.startswith('**') or stripped.startswith('*') or stripped.startswith('#'):
                    # Check if it's a Python comment (starts with #) - keep those
                    if not stripped.startswith('#'):
                        continue
                # Skip lines that are markdown headers
                if stripped.startswith('##') or stripped.startswith('###'):
                    continue
                final_lines.append(line)
            
            corrected_code = '\n'.join(final_lines).strip()
            
            logger.info("Gemini validation completed, code corrected")
            return corrected_code
            
        except Exception as e:
            logger.warning(f"Gemini validation failed: {e}, returning original refactored code")
            return refactored_code
    
    def _add_exception_handling(self, code: str) -> str:
        """Add exception handling transformations for all AWS services"""
        # Ensure os is imported if not already
        if 'os.' in code and 'import os' not in code:
            # Add import at the beginning if not present
            lines = code.split('\n')
            if not any('import os' in line for line in lines[:10]):
                code = 'import os\n' + code
        
        # Replace botocore exceptions imports
        # Handle multiple imports on one line first (most specific pattern first)
        if re.search(r'from botocore\.exceptions import.*NoCredentialsError.*ClientError', code) or \
           re.search(r'from botocore\.exceptions import.*ClientError.*NoCredentialsError', code):
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
        # Handle BotoCoreError and other botocore exceptions (catch-all)
        code = re.sub(
            r'from botocore\.exceptions import\s+.*',
            'from google.api_core import exceptions',
            code
        )
        
        # Replace exception usage (after imports are fixed)
        # Only replace if not in a string literal
        lines = code.split('\n')
        result_lines = []
        in_string = False
        string_char = None
        
        for i, line in enumerate(lines):
            # Track multiline strings
            if '"""' in line or "'''" in line:
                in_string = not in_string
                string_char = '"""' if '"""' in line else "'''"
            
            # Skip if in multiline string
            if in_string:
                result_lines.append(line)
                continue
            
            # Skip if in single-line string (simple check)
            # But allow replacement in except clauses
            if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
                # Check if it's an except clause - we can still replace there
                if re.search(r'except\s+(NoCredentialsError|ClientError|BotoCoreError)', line, re.IGNORECASE):
                    # Replace exception names in except clauses
                    line = re.sub(r'\bNoCredentialsError\b', 'DefaultCredentialsError', line)
                    line = re.sub(r'\bClientError\b', 'exceptions.GoogleAPIError', line)
                    line = re.sub(r'\bBotoCoreError\b', 'exceptions.GoogleAPIError', line)
                    result_lines.append(line)
                else:
                    # Might be in string, be conservative
                    result_lines.append(line)
                continue
            
            # Replace exception names
            line = re.sub(r'\bNoCredentialsError\b', 'DefaultCredentialsError', line)
            line = re.sub(r'\bClientError\b', 'exceptions.GoogleAPIError', line)
            line = re.sub(r'\bBotoCoreError\b', 'exceptions.GoogleAPIError', line)
            result_lines.append(line)
        
        code = '\n'.join(result_lines)
        
        # Ensure exceptions module is available if ClientError/BotoCoreError is used
        if 'exceptions.GoogleAPIError' in code and 'from google.api_core import exceptions' not in code:
            # Add import if not present
            if 'from google.api_core import exceptions' not in code:
                code = 'from google.api_core import exceptions\n' + code
        
        return code
    
    def _migrate_lambda_to_cloud_functions(self, code: str) -> tuple[str, dict]:
        """Migrate AWS Lambda to Google Cloud Functions with proper GCP patterns.
        
        Returns:
            tuple: (transformed_code, variable_mapping) where variable_mapping tracks
                   variable name changes (lambda_client → gcf_client, etc.)
        """
        variable_mapping = {}  # Track variable name changes
        
        # Store original code for variable detection
        original_code = code
        
        # Pattern 1: Detect Lambda client variables
        lambda_client_pattern = r'(\w+)\s*=\s*boto3\.client\([\'\"]lambda[\'\"].*?\)'
        lambda_matches = re.finditer(lambda_client_pattern, original_code, flags=re.DOTALL)
        for match in lambda_matches:
            var_name = match.group(1)
            if var_name not in variable_mapping:
                variable_mapping[var_name] = 'gcf_client'
        
        # Pattern 2: Common Lambda variable names
        if re.search(r'\blambda_client\b', original_code):
            variable_mapping['lambda_client'] = 'gcf_client'
        if re.search(r'\blambda_function\b', original_code):
            variable_mapping['lambda_function'] = 'gcf_function'
        
        # Replace Lambda client imports with GCP imports
        code = re.sub(r'^import boto3\s*$', 'import functions_framework\nfrom google.cloud import functions_v2', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'import functions_framework\nfrom google.cloud import functions_v2', code, flags=re.MULTILINE)
        
        # Apply variable renaming FIRST
        for old_var, new_var in variable_mapping.items():
            if old_var != new_var:
                lines = code.split('\n')
                renamed_lines = []
                for line in lines:
                    if line.strip().startswith('#'):
                        renamed_lines.append(line)
                        continue
                    pattern = rf'\b{re.escape(old_var)}\b(?=\s*[.=\(\)\[\],:]|\s*$)'
                    protected_line = re.sub(pattern, new_var, line)
                    renamed_lines.append(protected_line)
                code = '\n'.join(renamed_lines)
        
        # Replace Lambda client instantiation (if still present after renaming)
        # This should happen AFTER variable renaming, so we match the renamed variable
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]lambda[\'\"].*?\)',
            r'\1 = functions_v2.FunctionServiceClient()  # GCP Cloud Functions client',
            code,
            flags=re.DOTALL
        )
        
        # Also replace any remaining lambda_client references that weren't caught
        code = re.sub(r'\blambda_client\b', 'gcf_client', code)
        
        # Handle S3 event trigger patterns FIRST (before handler transformation)
        # Pattern: event['Records'][0]['s3']['bucket']['name']
        # Replace nested patterns first
        code = re.sub(
            r'event\[[\'"]Records[\'"]\]\[(\d+)\]\[[\'"]s3[\'"]\]\[[\'"]bucket[\'"]\]\[[\'"]name[\'"]\]',
            r'event["Records"][\1]["bucket"]["name"]  # Updated for Cloud Storage event format',
            code
        )
        code = re.sub(
            r'record\[[\'"]s3[\'"]\]\[[\'"]bucket[\'"]\]\[[\'"]name[\'"]\]',
            r'record["bucket"]["name"]',
            code
        )
        code = re.sub(
            r'record\[[\'"]s3[\'"]\]\[[\'"]object[\'"]\]\[[\'"]key[\'"]\]',
            r'record["name"]  # Cloud Storage event uses "name" instead of "key"',
            code
        )
        # Replace record['s3']['bucket'] -> record['bucket']
        code = re.sub(
            r'record\[[\'"]s3[\'"]\]\[[\'"]bucket[\'"]\]',
            r'record["bucket"]',
            code
        )
        code = re.sub(
            r'record\[[\'"]s3[\'"]\]\[[\'"]object[\'"]\]',
            r'record["object"]',
            code
        )
        # Also replace any remaining ['s3'] references in event records - be more aggressive
        # Replace record['s3'] -> record['bucket']
        code = re.sub(
            r'record\[[\'"]s3[\'"]\]',
            r'record["bucket"]',
            code
        )
        # Replace event['Records'][i]['s3'] -> event['Records'][i]['bucket']
        code = re.sub(
            r'event\[[\'"]Records[\'"]\]\[(\d+)\]\[[\'"]s3[\'"]\]',
            r'event["Records"][\1]["bucket"]',
            code
        )
        # Replace any ['s3'] pattern in dictionary access (but not in strings)
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            # Skip if in string
            if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
                result_lines.append(line)
                continue
            # Replace ['s3'] -> ['bucket']
            line = re.sub(r'\[[\'"]s3[\'"]\]', r'["bucket"]', line)
            result_lines.append(line)
        code = '\n'.join(result_lines)
        
        # Replace Lambda function handler patterns
        # Pattern: def lambda_handler(event, context):
        # For GCS-triggered functions, use background function signature
        def replace_lambda_handler(match):
            # Check if this is an S3-triggered Lambda (has event['Records'] pattern)
            # If so, convert to GCS background function
            # Otherwise, use HTTP function
            return 'def process_gcs_file(data, context):\n    """\n    Background Cloud Function triggered by a new file in Cloud Storage.\n    The \'data\' parameter contains the bucket and file information.\n    The \'context\' parameter provides event metadata.\n    """'
        
        # First, check if it's an S3-triggered Lambda
        is_s3_triggered = re.search(r'event\[[\'"]Records[\'"]\]', code) or re.search(r'record_event\[[\'"]s3[\'"]\]', code)
        
        if is_s3_triggered:
            # Replace with GCS background function handler
            code = re.sub(
                r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
                'def process_gcs_file(data, context):\n    """\n    Background Cloud Function triggered by a new file in Cloud Storage.\n    The \'data\' parameter contains the bucket and file information.\n    The \'context\' parameter provides event metadata.\n    """',
                code,
                flags=re.IGNORECASE
            )
            
            # Replace event['Records'] loop with GCS event structure
            # Pattern: for record_event in event['Records']:
            code = re.sub(
                r'for\s+record_event\s+in\s+event\[[\'"]Records[\'"]\]\s*:',
                '# GCS background function receives single file event, not a list\n    # Process the single file event',
                code
            )
            
            # Replace event['Records'] access with direct data access
            # Pattern: if not event.get('Records'):
            code = re.sub(
                r'if\s+not\s+event\.get\([\'"]Records[\'"]\)\s*:',
                'if not data.get(\'bucket\') or not data.get(\'name\'):',
                code
            )
            
            # Replace record_event['s3']['bucket']['name'] -> data['bucket']
            code = re.sub(
                r'record_event\[[\'"]s3[\'"]\]\[[\'"]bucket[\'"]\]\[[\'"]name[\'"]\]',
                'data.get(\'bucket\')',
                code
            )
            code = re.sub(
                r'record_event\[[\'"]s3[\'"]\]\[[\'"]object[\'"]\]\[[\'"]key[\'"]\]',
                'data.get(\'name\')',
                code
            )
            
            # Replace bucket_name = record_event['s3']['bucket']['name']
            code = re.sub(
                r'bucket_name\s*=\s*record_event\[[\'"]s3[\'"]\]\[[\'"]bucket[\'"]\]\[[\'"]name[\'"]\]',
                'bucket_name = data.get(\'bucket\')',
                code
            )
            code = re.sub(
                r'object_key\s*=\s*record_event\[[\'"]s3[\'"]\]\[[\'"]object[\'"]\]\[[\'"]key[\'"]\]',
                'object_key = data.get(\'name\')',
                code
            )
        else:
            # HTTP-triggered function
            code = re.sub(
                r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
                '@functions_framework.http\ndef function_handler(request):\n    """\n    Google Cloud Function HTTP handler.\n    Args:\n        request (flask.Request): The request object.\n    Returns:\n        The response text or JSON.\n    """\n    request_json = request.get_json(silent=True)\n    event = request_json if request_json else {}',
                code,
                flags=re.IGNORECASE
            )
        
        # Replace AWS environment variables FIRST (before S3 migration)
        # Handle os.environ.get() with optional default - be more aggressive
        code = re.sub(r"os\.environ\.get\(['\"]S3_BUCKET_NAME['\"](?:,\s*[^)]+)?\)", "os.getenv('GCS_BUCKET_NAME')", code)
        code = re.sub(r"os\.environ\[['\"]S3_BUCKET_NAME['\"]\]", "os.getenv('GCS_BUCKET_NAME')", code)
        code = re.sub(r"os\.environ\.get\(['\"]AWS_REGION['\"](?:,\s*[^)]+)?\)", "os.getenv('GCP_REGION')", code)
        code = re.sub(r"os\.environ\[['\"]AWS_REGION['\"]\]", "os.getenv('GCP_REGION')", code)
        code = re.sub(r"os\.environ\.get\(['\"]AWS_LAMBDA_FUNCTION_NAME['\"](?:,\s*[^)]+)?\)", "os.getenv('GCP_FUNCTION_NAME')", code)
        code = re.sub(r"os\.environ\[['\"]AWS_LAMBDA_FUNCTION_NAME['\"]\]", "os.getenv('GCP_FUNCTION_NAME')", code)
        
        # Also replace S3_BUCKET_NAME in any context (not just os.environ)
        code = re.sub(r"['\"]S3_BUCKET_NAME['\"]", "'GCS_BUCKET_NAME'", code)
        
        # Ensure os is imported if environment variables are used
        if re.search(r'os\.(getenv|environ)', code) and 'import os' not in code:
            lines = code.split('\n')
            if not any('import os' in line for line in lines[:10]):
                # Insert after functions_framework import if present
                if 'import functions_framework' in code:
                    code = code.replace('import functions_framework', 'import functions_framework\nimport os', 1)
                elif 'from google.cloud import' in code:
                    # Insert after GCP imports
                    code = re.sub(r'(from google\.cloud import[^\n]+)', r'\1\nimport os', code, count=1)
                else:
                    code = 'import os\n' + code
        
        # If Lambda handler contains S3 code, migrate that too
        # Check for S3 patterns AFTER Lambda handler transformation
        # Be more aggressive in detection - check for any S3 patterns
        has_s3 = (re.search(r'boto3\.(client|resource)\([\'\"]s3[\'\"]', code, re.IGNORECASE) or 
                  re.search(r'\.(get_object|put_object|upload_file|download_file)', code) or
                  re.search(r'event\[[\'"]Records[\'"]\]', code) or
                  re.search(r'Bucket=', code) or
                  re.search(r'Key=', code) or
                  re.search(r'record\[[\'"]s3[\'"]\]', code))
        
        if has_s3:
            # Migrate S3 code inside Lambda handler
            try:
                s3_code, s3_var_mapping = self._migrate_s3_to_gcs(code)
                # Merge variable mappings
                variable_mapping.update(s3_var_mapping)
                code = s3_code
            except Exception as e:
                import logging
                logging.warning(f"S3 migration in Lambda handler failed: {e}")
                # Try to at least replace boto3.client('s3') manually - handle with region_name too
                code = re.sub(r'boto3\.client\([\'\"]s3[\'\"][^\)]*\)', 'storage.Client()', code)
                code = re.sub(r'boto3\.resource\([\'\"]s3[\'\"][^\)]*\)', 'storage.Client()', code)
                # Ensure storage is imported
                if 'from google.cloud import storage' not in code:
                    code = 'from google.cloud import storage\n' + code
                # Replace S3 operations manually
                code = re.sub(r'(\w+)\.get_object\(Bucket=([^,]+),\s*Key=([^\)]+)\)', 
                             r'bucket = gcs_client.bucket(\2)\n    blob = bucket.blob(\3)\n    content = blob.download_as_text()', code)
                # Replace s3 variable references - be more aggressive
                # First replace s3 = storage.Client() -> gcs_client = storage.Client()
                code = re.sub(r'\bs3\s*=\s*storage\.Client\(\)', 'gcs_client = storage.Client()', code)
                # Replace s3 = boto3.client('s3') -> gcs_client = storage.Client()
                code = re.sub(r'\bs3\s*=\s*boto3\.client\([\'\"]s3[\'\"][^\)]*\)', 'gcs_client = storage.Client()', code)
                # Replace s3 = boto3.resource('s3') -> gcs_client = storage.Client()
                code = re.sub(r'\bs3\s*=\s*boto3\.resource\([\'\"]s3[\'\"][^\)]*\)', 'gcs_client = storage.Client()', code)
                # Then replace all s3. method calls with gcs_client.
                lines = code.split('\n')
                result_lines = []
                for line in lines:
                    # Skip if in string
                    if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
                        result_lines.append(line)
                        continue
                    # Replace s3 = ... -> gcs_client = ...
                    if re.search(r'\bs3\s*=\s*', line):
                        line = re.sub(r'\bs3\s*=\s*', 'gcs_client = ', line)
                    # Replace s3. with gcs_client.
                    if re.search(r'\bs3\s*\.', line):
                        line = re.sub(r'\bs3\s*\.', 'gcs_client.', line)
                    # Replace standalone s3 variable when used as client
                    elif re.search(r'\bs3\b', line) and re.search(r'\bs3\s*\.', line):
                        line = re.sub(r'\bs3\b(?=\s*\.)', 'gcs_client', line)
                    result_lines.append(line)
                code = '\n'.join(result_lines)
                # Final pass: replace any remaining s3 variable references
                code = re.sub(r'\bs3\s*\.', 'gcs_client.', code)
                # Continue with Lambda transformation even if S3 migration fails
        
        # Replace Lambda invocation calls with proper GCP HTTP requests
        # Handle both: response = client.invoke(...) and client.invoke(...)
        def replace_invoke_assignment(match):
            # Pattern: response = client.invoke(...)
            var_name = match.group(1)
            client_var = match.group(2)
            function_name = match.group(3).strip('\'"')
            invocation_type = match.group(4).strip('\'"') if match.group(4) else 'RequestResponse'
            payload = match.group(5)
            payload_str = payload.strip()
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport os\nimport requests\n# For HTTP-triggered functions, use the function URL\n# Use GCP environment variables\nproject_id = os.getenv(\'GCP_PROJECT_ID\', \'your-project-id\')\nregion = os.getenv(\'GCP_REGION\', \'us-central1\')\nfunction_url = f"https://{{region}}-{{project_id}}.cloudfunctions.net/{function_name}"\n{var_name} = requests.post(function_url, json={payload_str})\nresult = {var_name}.json() if {var_name}.headers.get(\'content-type\', \'\').startswith(\'application/json\') else {var_name}.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
        def replace_invoke_direct(match):
            # Pattern: client.invoke(...)
            client_var = match.group(1)
            function_name = match.group(2).strip('\'"')
            invocation_type = match.group(3).strip('\'"') if match.group(3) else 'RequestResponse'
            payload = match.group(4)
            payload_str = payload.strip()
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport os\nimport requests\n# For HTTP-triggered functions, use the function URL\n# Use GCP environment variables\nproject_id = os.getenv(\'GCP_PROJECT_ID\', \'your-project-id\')\nregion = os.getenv(\'GCP_REGION\', \'us-central1\')\nfunction_url = f"https://{{region}}-{{project_id}}.cloudfunctions.net/{function_name}"\nresponse = requests.post(function_url, json={payload_str})\nresult = response.json() if response.headers.get(\'content-type\', \'\').startswith(\'application/json\') else response.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
        # Replace Lambda invocation calls - handle multi-line patterns
        # Use a more robust approach: find all invoke calls first, then replace them
        # This handles both single-line and multi-line patterns
        
        # Pattern for invoke calls (handles multi-line with DOTALL)
        invoke_pattern = r'(\w+)\s*=\s*(\w+)\.invoke\s*\(\s*FunctionName\s*=\s*([^,]+)\s*,\s*InvocationType\s*=\s*([^,]+)?\s*,\s*Payload\s*=\s*([^\)]+)\s*\)'
        
        def replace_invoke_full(match):
            var_name = match.group(1)
            function_name = match.group(3).strip('\'"')
            payload = match.group(5).strip().strip('\'"')
            # Parse payload - if it's a JSON string, convert it properly
            if payload.startswith('\'') and payload.endswith('\''):
                payload = payload[1:-1]  # Remove quotes
            elif payload.startswith('"') and payload.endswith('"'):
                payload = payload[1:-1]
            # Return properly formatted code block
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport os\nimport requests\n# For HTTP-triggered functions, use the function URL\n# Use GCP environment variables\nproject_id = os.getenv(\'GCP_PROJECT_ID\', \'your-project-id\')\nregion = os.getenv(\'GCP_REGION\', \'us-central1\')\nfunction_url = f"https://{{region}}-{{project_id}}.cloudfunctions.net/{function_name}"\n{var_name} = requests.post(function_url, json={payload})\nresult = {var_name}.json() if {var_name}.headers.get(\'content-type\', \'\').startswith(\'application/json\') else {var_name}.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
        # Replace multi-line invoke calls
        code = re.sub(invoke_pattern, replace_invoke_full, code, flags=re.DOTALL)
        
        # Also handle direct invoke (without assignment)
        direct_invoke_pattern = r'(\w+)\.invoke\s*\(\s*FunctionName\s*=\s*([^,]+)\s*,\s*InvocationType\s*=\s*([^,]+)?\s*,\s*Payload\s*=\s*([^\)]+)\s*\)'
        def replace_invoke_direct_full(match):
            function_name = match.group(2).strip('\'"')
            payload = match.group(4).strip().strip('\'"')
            # Parse payload - if it's a JSON string, convert it properly
            if payload.startswith('\'') and payload.endswith('\''):
                payload = payload[1:-1]
            elif payload.startswith('"') and payload.endswith('"'):
                payload = payload[1:-1]
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport os\nimport requests\n# For HTTP-triggered functions, use the function URL\n# Use GCP environment variables\nproject_id = os.getenv(\'GCP_PROJECT_ID\', \'your-project-id\')\nregion = os.getenv(\'GCP_REGION\', \'us-central1\')\nfunction_url = f"https://{{region}}-{{project_id}}.cloudfunctions.net/{function_name}"\nresponse = requests.post(function_url, json={payload})\nresult = response.json() if response.headers.get(\'content-type\', \'\').startswith(\'application/json\') else response.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
        code = re.sub(direct_invoke_pattern, replace_invoke_direct_full, code, flags=re.DOTALL)
        
        # Replace create_function with proper GCP deployment pattern
        # Use regex with DOTALL to handle multi-line patterns
        create_function_pattern = r'(\w+)\.create_function\s*\(\s*FunctionName\s*=\s*([^,]+)\s*,\s*Runtime\s*=\s*([^,]+)\s*,\s*Role\s*=\s*([^,]+)\s*,\s*Handler\s*=\s*([^,]+)\s*,\s*Code\s*=\s*([^\)]+)\s*\)'
        
        def replace_create_function_full(match):
            function_name = match.group(2).strip('\'"')
            runtime = match.group(3).strip('\'"')
            handler = match.group(5).strip('\'"')
            return f'### 🚀 Deploy Cloud Function\n# Cloud Functions are deployed via gcloud CLI or Cloud Build\n# Example gcloud command:\n# gcloud functions deploy {function_name} \\\\\n#     --runtime={runtime} \\\\\n#     --trigger=http \\\\\n#     --entry-point={handler} \\\\\n#     --source=.\n#\n# Or use the Cloud Functions client for programmatic deployment:\nfrom google.cloud.functions_v2 import Function, CreateFunctionRequest\ngcf_client = functions_v2.FunctionServiceClient()\n# Note: Full deployment requires Cloud Build setup - see GCP documentation'
        
        code = re.sub(create_function_pattern, replace_create_function_full, code, flags=re.DOTALL)
        
        # Remove AWS Lambda comments - be more careful to remove entire comment lines
        code = re.sub(r'#\s*AWS\s+Lambda\s+example.*?\n', '# 🌟 Google Cloud Functions Example\n', code, flags=re.IGNORECASE)
        # Remove comment lines that contain AWS Lambda references
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip lines that are only AWS Lambda comments
            if re.match(r'^\s*#.*?AWS.*?Lambda.*?$', line, re.IGNORECASE):
                continue
            # Skip lines that are only Lambda comments (but keep other comments)
            if re.match(r'^\s*#.*?Lambda.*?$', line, re.IGNORECASE) and 'Cloud Function' not in line:
                continue
            cleaned_lines.append(line)
        code = '\n'.join(cleaned_lines)
        
        # Clean up multiple blank lines
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        # If Lambda handler contains S3 code, migrate that too
        # Check for S3 patterns AFTER Lambda handler transformation
        if re.search(r'boto3\.(client|resource)\([\'\"]s3[\'\"]', code, re.IGNORECASE):
            # Migrate S3 code inside Lambda handler
            try:
                s3_code, s3_var_mapping = self._migrate_s3_to_gcs(code)
                # Merge variable mappings
                variable_mapping.update(s3_var_mapping)
                code = s3_code
            except Exception as e:
                import logging
                logging.warning(f"S3 migration in Lambda handler failed: {e}")
                # Continue with Lambda transformation even if S3 migration fails
        
        # Replace AWS environment variables in Lambda handler
        code = re.sub(r"os\.environ\.get\(['\"]S3_BUCKET_NAME['\"](?:,\s*[^)]+)?\)", "os.getenv('GCS_BUCKET_NAME')", code)
        code = re.sub(r"os\.environ\[['\"]S3_BUCKET_NAME['\"]\]", "os.getenv('GCS_BUCKET_NAME')", code)
        
        # Final pass: ensure s3 variables are replaced with gcs_client
        # Replace s3 = storage.Client() -> gcs_client = storage.Client()
        code = re.sub(r'\bs3\s*=\s*storage\.Client\(\)', 'gcs_client = storage.Client()', code)
        # Replace s3. method calls with gcs_client.
        code = re.sub(r'\bs3\s*\.', 'gcs_client.', code)
        # Replace standalone s3 variable when used as client
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            # Skip if in string
            if line.count('"') % 2 == 1 or line.count("'") % 2 == 1:
                result_lines.append(line)
                continue
            # Replace s3 = ... -> gcs_client = ...
            if re.search(r'\bs3\s*=\s*', line):
                line = re.sub(r'\bs3\s*=\s*', 'gcs_client = ', line)
            # Replace s3. with gcs_client.
            if re.search(r'\bs3\s*\.', line):
                line = re.sub(r'\bs3\s*\.', 'gcs_client.', line)
            result_lines.append(line)
        code = '\n'.join(result_lines)
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)
        
        return code, variable_mapping
    
    def _migrate_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB to Google Cloud Firestore"""
        # Store original code for Gemini validation
        original_code = code
        
        # Detect if this is a migration script (reads from DynamoDB, writes to Firestore)
        # Migration scripts typically have: scan(), get_item(), query() AND put_item()/batch_write_item()
        is_migration_script = (
            re.search(r'\.(scan|get_item|query)\(', code, re.IGNORECASE) and
            re.search(r'\.(put_item|batch_write_item)\(', code, re.IGNORECASE)
        )
        
        if is_migration_script:
            # MIGRATION SCRIPT MODE: Preserve DynamoDB read operations, replace write operations
            return self._migrate_dynamodb_migration_script(code, original_code)
        
        # APPLICATION CODE MODE: Replace all DynamoDB with Firestore
        # CRITICAL FIRST PASS: Catch ALL boto3.client('dynamodb') patterns BEFORE anything else
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]dynamodb[\'\"][^\)]*\)',
            r'\1 = firestore.Client()',
            code,
            flags=re.DOTALL | re.IGNORECASE
        )
        code = re.sub(r'\bdynamodb_client\s*=\s*', 'firestore_db = ', code)
        code = re.sub(r'\bdynamodb_client\.', 'firestore_db.', code)
        code = re.sub(r'\bdynamodb_client\b', 'firestore_db', code)
        
        # Replace DynamoDB imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import firestore', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import firestore', code, flags=re.MULTILINE)
        
        # Track variable name for DynamoDB resource/client
        dynamodb_var_match = re.search(r'(\w+)\s*=\s*boto3\.(resource|client)\([\'\"]dynamodb[\'\"]', code)
        dynamodb_var = dynamodb_var_match.group(1) if dynamodb_var_match else 'dynamodb'
        db_var = 'db' if dynamodb_var == 'dynamodb' else f'{dynamodb_var}_db'
        
        # Replace DynamoDB resource (common pattern)
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.resource\([\'\"]dynamodb[\'\"].*?\)',
            rf'{db_var} = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace DynamoDB client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]dynamodb[\'\"].*?\)',
            rf'{db_var} = firestore.Client()',
            code,
            flags=re.DOTALL
        )
        
        # Replace variable references BEFORE table operations
        if dynamodb_var != db_var:
            # Replace dynamodb.Table -> db.collection
            code = re.sub(rf'\b{dynamodb_var}\b\.Table', f'{db_var}.collection', code)
            # Replace other dynamodb references
            code = re.sub(rf'\b{dynamodb_var}\b(?=\s*\.)', db_var, code)
        
        # Replace table operations with collection/document operations
        # First, replace Table() calls: db_var.Table('name') -> db_var.collection('name')
        code = re.sub(
            rf'{db_var}\.Table\(([^\)]+)\)',
            rf'{db_var}.collection(\1)',
            code
        )
        
        # Also handle cases where variable name is 'table' - rename to 'collection'
        # But be careful - only if it's clearly a DynamoDB table
        # Replace table = db.Table -> collection = db.collection
        code = re.sub(r'\btable\s*=\s*(\w+)\.Table', r'collection = \1.collection', code)
        code = re.sub(r'\btable\.put_item', r'collection.document().set', code)
        code = re.sub(r'\btable\.get_item', r'collection.document', code)
        
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
        
        # Replace batch_writer -> batch operations
        # Pattern: with table.batch_writer() as batch:
        code = re.sub(
            r'with\s+(\w+)\.batch_writer\(\)\s+as\s+(\w+):',
            r'batch = firestore_db.batch()\nwith batch:',
            code
        )
        # Replace batch.put_item() inside batch_writer context
        # This should match batch.put_item(Item={...}) where batch is the context variable
        code = re.sub(
            r'(\w+)\.put_item\(Item=([^\)]+)\)',
            r'doc_ref = collection_ref.document()\n    batch.set(doc_ref, \2)',
            code
        )
        
        # Replace dynamodb_client.batch_write_item() -> Firestore batch operations
        # Pattern: dynamodb_client.batch_write_item(RequestItems={TABLE_NAME: [PutRequest: {Item: {...}}]})
        def replace_batch_write_item(match):
            client_var = match.group(1)
            table_name = match.group(2) if len(match.groups()) >= 2 else 'DYNAMODB_TABLE_NAME'
            # Extract items from PutRequest list
            return f'batch = firestore_db.batch()\ncollection_ref = firestore_db.collection({table_name})\n# Process items in batches of 500 (Firestore limit)\nfor item in items:\n    doc_id = item.pop(\'uuid\', str(uuid.uuid4()))\n    doc_ref = collection_ref.document(doc_id)\n    batch.set(doc_ref, item)\nbatch.commit()'
        
        code = re.sub(
            r'(\w+)\.batch_write_item\(\s*RequestItems\s*=\s*\{([^:]+):\s*\[([^\]]+)\]\}\s*\)',
            replace_batch_write_item,
            code,
            flags=re.DOTALL
        )
        
        # Also handle simpler pattern: batch_write_item(RequestItems={TABLE: batch})
        code = re.sub(
            r'(\w+)\.batch_write_item\(\s*RequestItems\s*=\s*\{([^}]+)\}\s*\)',
            replace_batch_write_item,
            code,
            flags=re.DOTALL
        )
        
        # Replace DynamoDB item format {'S': 'value'} -> native Python dicts
        # Pattern: {'S': 'value'} -> 'value'
        code = re.sub(
            r'\{\s*[\'"]S[\'"]\s*:\s*([^}]+)\s*\}',
            r'\1',
            code
        )
        code = re.sub(
            r'\{\s*[\'"]N[\'"]\s*:\s*([^}]+)\s*\}',
            r'int(\1)',
            code
        )
        
        # Replace scan() -> collection.stream()
        code = re.sub(
            r'(\w+)\.scan\(\)',
            r'\1.stream()',
            code
        )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)
        
        return code
    
    def _migrate_dynamodb_migration_script(self, code: str, original_code: str) -> str:
        """
        Migrate DynamoDB to Firestore migration script.
        Preserves DynamoDB read operations (scan, get_item, query) and replaces write operations.
        """
        # Ensure boto3 import is present (for reading from DynamoDB)
        if 'import boto3' not in code:
            # Add boto3 import at the top if not present
            code = 'import boto3\n' + code
        
        # Ensure Firestore imports are present (for writing to Firestore)
        if 'from google.cloud import firestore' not in code:
            if 'import firebase_admin' not in code:
                # Add Firestore imports
                code = 'import firebase_admin\nfrom firebase_admin import credentials, firestore\nfrom decimal import Decimal\n' + code
            elif 'from firebase_admin import' not in code:
                code = code.replace('import firebase_admin', 'import firebase_admin\nfrom firebase_admin import credentials, firestore\nfrom decimal import Decimal')
        
        # Find DynamoDB client/resource variable names (for reading)
        dynamodb_resource_match = re.search(r'(\w+)\s*=\s*boto3\.resource\([\'\"]dynamodb[\'\"][^\)]*\)', code)
        dynamodb_client_match = re.search(r'(\w+)\s*=\s*boto3\.client\([\'\"]dynamodb[\'\"][^\)]*\)', code)
        
        # Preserve DynamoDB resource/client initialization (for reading)
        # Don't replace these - they're needed for reading from DynamoDB
        
        # Add Firestore client initialization (for writing)
        # Find where DynamoDB client/resource is initialized and add Firestore client nearby
        if dynamodb_resource_match or dynamodb_client_match:
            # Find the initialization line
            init_pattern = r'(\w+)\s*=\s*boto3\.(resource|client)\([\'\"]dynamodb[\'\"][^\)]*\)'
            def add_firestore_init(match):
                dynamodb_var = match.group(1)
                # Add Firestore initialization after DynamoDB initialization
                return match.group(0) + f'\n\n# Initialize Firestore for writing\nif not firebase_admin._apps:\n    cred = credentials.Certificate(GOOGLE_KEY_PATH)\n    firebase_admin.initialize_app(cred)\n\nfirestore_db = firestore.Client()'
            code = re.sub(init_pattern, add_firestore_init, code, count=1)
        else:
            # No DynamoDB initialization found, add both
            code = '# Initialize AWS DynamoDB (for reading)\ndynamodb_resource = boto3.resource(\'dynamodb\', region_name=DYNAMO_REGION)\nsource_table = dynamodb_resource.Table(DYNAMO_TABLE_NAME)\n\n# Initialize Google Firestore (for writing)\nif not firebase_admin._apps:\n    cred = credentials.Certificate(GOOGLE_KEY_PATH)\n    firebase_admin.initialize_app(cred)\n\nfirestore_db = firestore.Client()\n' + code
        
        # Replace write operations: put_item() -> Firestore set()
        # Pattern: table.put_item(Item={...}) -> firestore_db.collection(...).document().set(...)
        def replace_put_item(match):
            table_var = match.group(1)
            item = match.group(2)
            # Try to extract table name from context or use a variable
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
        
        # Add helper function for Decimal conversion if not present
        if 'def convert_decimal' not in code:
            helper_func = '''def convert_decimal(obj):
    """
    Recursively converts Decimal types (from DynamoDB) to standard Python
    int/float types, as Firestore does not support Decimal natively.
    """
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    else:
        return obj
'''
            # Insert before the main migration function
            if 'def migrate' in code:
                code = code.replace('def migrate', helper_func + '\n\ndef migrate', 1)
            else:
                code = helper_func + '\n\n' + code
        
        # Keep scan(), get_item(), query() operations as DynamoDB operations
        # These should remain unchanged - they're reading from DynamoDB
        
        # Add configuration constants if not present
        if 'DYNAMO_TABLE_NAME' not in code:
            config = '''# --- CONFIGURATION ---
DYNAMO_TABLE_NAME = 'SourceDynamoTable'
DYNAMO_REGION = 'us-east-1'
FIRESTORE_COLLECTION = 'DestinationCollection'
GOOGLE_KEY_PATH = 'path/to/service-account.json'
PRIMARY_KEY_FIELD = 'UserId'  # Field in DynamoDB to use as Document ID in Firestore

'''
            # Insert after imports
            import_end = max(code.rfind('import '), code.rfind('from '))
            if import_end != -1:
                next_line = code.find('\n', import_end)
                if next_line != -1:
                    code = code[:next_line+1] + config + code[next_line+1:]
            else:
                code = config + code
        
        return code
    
    def _migrate_sqs_to_pubsub(self, code: str) -> str:
        """Migrate AWS SQS to Google Cloud Pub/Sub"""
        # Store original code for Gemini validation
        original_code = code
        
        # CRITICAL FIRST PASS: Catch ALL boto3.client('sqs') patterns BEFORE anything else
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code,
            flags=re.DOTALL | re.IGNORECASE
        )
        code = re.sub(r'\bsqs_client\s*=\s*', 'pubsub_publisher = ', code)
        code = re.sub(r'\bsqs_client\.', 'pubsub_publisher.', code)
        code = re.sub(r'\bsqs_client\b', 'pubsub_publisher', code)
        
        # Replace SQS imports FIRST
        code = re.sub(r'^import boto3\s*$', 'import os\nfrom google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'import os\nfrom google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        # Also handle if boto3 import is still present
        if 'import boto3' in code and 'from google.cloud import pubsub_v1' not in code:
            code = re.sub(r'import boto3', 'import os\nfrom google.cloud import pubsub_v1', code, count=1)
        
        # Track variable name for SQS client BEFORE replacement
        sqs_var_match = re.search(r'(\w+)\s*=\s*boto3\.client\([\'\"]sqs[\'\"][^\)]*\)', code)
        sqs_var = sqs_var_match.group(1) if sqs_var_match else 'sqs'
        publisher_var = 'publisher' if sqs_var == 'sqs' else f'{sqs_var}_publisher'
        
        # Replace SQS client instantiation - handle with region_name and config too
        # Must match: sqs = boto3.client('sqs') or sqs = boto3.client('sqs', region_name='...')
        # Use a function to preserve the variable name
        def replace_sqs_client(match):
            var_name = match.group(1)
            return f'{publisher_var} = pubsub_v1.PublisherClient()'
        
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sqs[\'\"][^\)]*\)',
            replace_sqs_client,
            code,
            flags=re.DOTALL
        )
        
        # Replace all sqs. method calls with publisher. BEFORE URL replacement
        code = re.sub(rf'\b{sqs_var}\b\.', f'{publisher_var}.', code)
        
        # Replace queue URL assignments (remove them, not needed for Pub/Sub)
        # Handle both variable assignments and direct usage - be more aggressive
        # Replace SQS URLs completely - handle both single and double quotes
        code = re.sub(
            r'(\w+)\s*=\s*[\'"]https://sqs\.[^\'"]+[\'"]',
            rf'# Queue URL not needed for Pub/Sub - use topic_path instead',
            code
        )
        # Also replace any remaining SQS URL strings (but not in comments)
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            if line.strip().startswith('#'):
                result_lines.append(line)
                continue
            # Replace SQS URLs
            line = re.sub(r'[\'"]https://sqs\.[^\'"]+[\'"]', r'# SQS URL replaced', line)
            result_lines.append(line)
        code = '\n'.join(result_lines)
        # Also replace queue URLs in function calls - handle variable references too
        code = re.sub(
            r'QueueUrl=[\'"]https://sqs\.[^\'"]+[\'"]',
            r'# QueueUrl parameter removed - use topic_path instead',
            code
        )
        # Don't replace QueueUrl=variable_name as it might break code
        # Instead, replace queue_url variable usage after send_message transformation
        # Replace any remaining queue_url variable references (but not in strings)
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            if line.count('"') % 2 == 0 and line.count("'") % 2 == 0:
                # Replace queue_url variable references
                line = re.sub(r'\bqueue_url\b(?=\s*[,\)])', 'topic_path', line)
            result_lines.append(line)
        code = '\n'.join(result_lines)
        
        # Replace SQS send_message -> Pub/Sub publish
        # Pattern: sqs.send_message(QueueUrl=url, MessageBody=body)
        # Extract topic name from queue URL if possible, otherwise use default
        def replace_send_message(match):
            client_var = match.group(1)
            queue_url_param = match.group(2).strip()
            message_body = match.group(3)
            # Try to extract topic name from queue URL (could be variable or string)
            queue_url = queue_url_param.strip('\'"')
            topic_match = re.search(r'/([^/]+)(?:\.fifo)?$', queue_url)
            topic_name = topic_match.group(1) if topic_match else 'topic-name'
            return f'import os\n    topic_path = {publisher_var}.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), os.getenv("GCP_PUBSUB_TOPIC_ID", "{topic_name}"))\n    future = {publisher_var}.publish(topic_path, {message_body}.encode("utf-8"))'
        
        # Handle send_message with QueueUrl parameter
        code = re.sub(
            r'(\w+)\.send_message\(QueueUrl=([^,]+),\s*MessageBody=([^,\)]+)\)',
            replace_send_message,
            code
        )
        
        # Also handle send_message with FIFO parameters
        code = re.sub(
            r'(\w+)\.send_message\(\s*QueueUrl=([^,]+),\s*MessageBody=([^,]+),\s*MessageGroupId=([^,]+),\s*MessageDeduplicationId=([^\)]+)\)',
            replace_send_message,
            code
        )
        
        # Replace receive_message -> Pub/Sub pull
        def replace_receive_message(match):
            client_var = match.group(1)
            queue_url_param = match.group(2).strip().strip('\'"')
            # Try to extract subscription name from queue URL
            sub_match = re.search(r'/([^/]+)(?:\.fifo)?$', queue_url_param)
            sub_name = sub_match.group(1) if sub_match else 'subscription-name'
            return f'import os\n    subscriber = pubsub_v1.SubscriberClient()\n    subscription_path = subscriber.subscription_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), os.getenv("GCP_PUBSUB_SUBSCRIPTION_ID", "{sub_name}"))\n    response = subscriber.pull(request={{"subscription": subscription_path, "max_messages": 1}})'
        
        code = re.sub(
            r'(\w+)\.receive_message\(QueueUrl=([^,\)]+)\)',
            replace_receive_message,
            code
        )
        
        # Replace delete_message -> Pub/Sub acknowledge
        code = re.sub(
            r'(\w+)\.delete_message\(QueueUrl=([^,]+),\s*ReceiptHandle=([^,\)]+)\)',
            r'subscriber.acknowledge(request={{"subscription": subscription_path, "ack_ids": [\3]}})',
            code
        )
        
        # Replace FIFO queue patterns (MessageGroupId, MessageDeduplicationId)
        # Pub/Sub doesn't have exact FIFO equivalent, but we can use ordering keys
        # Remove these parameters from function calls
        code = re.sub(
            r',\s*MessageGroupId=([^,]+)',
            r'  # MessageGroupId -> Use ordering_key in Pub/Sub for message ordering',
            code
        )
        code = re.sub(
            r'MessageGroupId=([^,]+),',
            r'# MessageGroupId -> Use ordering_key in Pub/Sub for message ordering\n    ',
            code
        )
        code = re.sub(
            r',\s*MessageDeduplicationId=([^,]+)',
            r'  # MessageDeduplicationId -> Pub/Sub handles deduplication automatically',
            code
        )
        code = re.sub(
            r'MessageDeduplicationId=([^,]+),',
            r'# MessageDeduplicationId -> Pub/Sub handles deduplication automatically\n    ',
            code
        )
        
        # Remove any remaining references to the old SQS variable name in method calls
        if sqs_var != publisher_var:
            # Replace sqs.send_message -> publisher.publish, etc.
            code = re.sub(rf'\b{sqs_var}\b\.send_message', f'{publisher_var}.publish', code)
            code = re.sub(rf'\b{sqs_var}\b\.receive_message', 'subscriber.pull', code)
            code = re.sub(rf'\b{sqs_var}\b\.delete_message', 'subscriber.acknowledge', code)
            # Replace standalone sqs variable references (but not in strings)
            lines = code.split('\n')
            result_lines = []
            for line in lines:
                if line.count('"') % 2 == 0 and line.count("'") % 2 == 0:
                    line = re.sub(rf'\b{sqs_var}\b(?=\s*\.)', publisher_var, line)
                result_lines.append(line)
            code = '\n'.join(result_lines)
        
        # Final cleanup: replace any remaining sqs.send_message patterns
        code = re.sub(r'sqs\.send_message', 'publisher.publish', code)
        code = re.sub(r'sqs\.receive_message', 'subscriber.pull', code)
        
        # Ensure os is imported if not present
        if 'os.getenv' in code and 'import os' not in code:
            code = 'import os\n' + code
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)
        
        return code
    
    def _migrate_sns_to_pubsub(self, code: str) -> str:
        """Migrate AWS SNS to Google Cloud Pub/Sub"""
        # Store original code for Gemini validation
        original_code = code
        
        # CRITICAL FIRST PASS: Catch ALL boto3.client('sns') patterns BEFORE anything else
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\s*\(\s*[\'\"]sns[\'\"][^\)]*\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code,
            flags=re.DOTALL | re.IGNORECASE
        )
        code = re.sub(r'\bsns_client\s*=\s*', 'pubsub_publisher = ', code)
        code = re.sub(r'\bsns_client\.', 'pubsub_publisher.', code)
        code = re.sub(r'\bsns_client\b', 'pubsub_publisher', code)
        
        # Replace SNS imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        
        # Replace SNS publish -> Pub/Sub publish
        code = re.sub(
            r'(\w+)\.publish\(TopicArn=([^,]+),\s*Message=([^,\)]+)\)',
            r'import os\n    topic_path = \1.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), os.getenv("GCP_PUBSUB_TOPIC_ID", "topic-name"))\n    future = \1.publish(topic_path, \3.encode("utf-8"))',
            code
        )
        
        # Replace create_topic
        code = re.sub(
            r'(\w+)\.create_topic\(Name=([^,\)]+)\)',
            r'topic_path = \1.topic_path(os.getenv("GCP_PROJECT_ID", "your-project-id"), \2)\n    topic = \1.create_topic(request={"name": topic_path})',
            code
        )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)
        
        return code
    
    def _migrate_rds_to_cloud_sql(self, code: str) -> str:
        """Migrate AWS RDS to Google Cloud SQL"""
        # Store original code for Gemini validation
        original_code = code
        
        # Replace boto3 RDS client imports
        code = re.sub(r'^import boto3\s*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', '', code, flags=re.MULTILINE)
        
        # Replace RDS client instantiation (remove it, not needed for Cloud SQL)
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]rds[\'\"].*?\)',
            r'# RDS management operations replaced with Cloud SQL Admin API if needed',
            code,
            flags=re.DOTALL
        )
        
        # Replace RDS database connection patterns
        if 'pymysql' in code:
            code = re.sub(
                r'import pymysql',
                'from google.cloud.sql.connector import Connector\nimport pymysql',
                code
            )
            code = re.sub(
                r'connection\s*=\s*pymysql\.connect\(host=([^,]+),\s*user=([^,]+),\s*password=([^,]+),\s*database=([^,\)]+)\)',
                r'import os\n    from google.cloud.sql.connector import Connector\n    connector = Connector()\n    connection_name = os.getenv("GCP_CLOUD_SQL_INSTANCE_CONNECTION_NAME", f\'{os.getenv("GCP_PROJECT_ID", "your-project-id")}:{os.getenv("GCP_REGION", "us-central1")}:INSTANCE\')\n    connection = connector.connect(\n        connection_name,\n        "pymysql",\n        user=\2,\n        password=\3,\n        db=\4\n    )',
                code
            )
        elif 'psycopg2' in code:
            code = re.sub(
                r'import psycopg2',
                'from google.cloud.sql.connector import Connector\nimport psycopg2',
                code
            )
            code = re.sub(
                r'connection\s*=\s*psycopg2\.connect\(host=([^,]+),\s*user=([^,]+),\s*password=([^,]+),\s*database=([^,\)]+)\)',
                r'import os\n    from google.cloud.sql.connector import Connector\n    connector = Connector()\n    connection_name = os.getenv("GCP_CLOUD_SQL_INSTANCE_CONNECTION_NAME", f\'{os.getenv("GCP_PROJECT_ID", "your-project-id")}:{os.getenv("GCP_REGION", "us-central1")}:INSTANCE\')\n    connection = connector.connect(\n        connection_name,\n        "psycopg2",\n        user=\2,\n        password=\3,\n        db=\4\n    )',
                code
            )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)
        
        return code

    def _migrate_cloudwatch_to_monitoring(self, code: str) -> str:
        """Migrate AWS CloudWatch to Google Cloud Monitoring"""
        # Store original code for Gemini validation
        original_code = code
        
        # Replace CloudWatch imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import monitoring_v3', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import monitoring_v3', code, flags=re.MULTILINE)

        # Replace CloudWatch client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]cloudwatch[\'\"].*?\)',
            r'\1 = monitoring_v3.MetricServiceClient()',
            code,
            flags=re.DOTALL
        )

        # Replace put_metric_data
        code = re.sub(
            r'(\w+)\.put_metric_data\(Namespace=([^,]+),\s*MetricData=\[([^,\)]+)\]\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    project_name = f"projects/{project_id}"\n    series = monitoring_v3.TimeSeries()\n    series.metric.type = os.getenv("GCP_MONITORING_METRIC_TYPE", "custom.googleapis.com/metric")\n    # Add metric data points',
            code
        )
        
        # Replace get_metric_statistics
        code = re.sub(
            r'(\w+)\.get_metric_statistics\(Namespace=([^,]+),\s*MetricName=([^,]+),\s*StartTime=([^,]+),\s*EndTime=([^,]+),\s*Period=([^,]+),\s*Statistics=\[([^,\)]+)\]\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    project_name = f"projects/{project_id}"\n    interval = monitoring_v3.TimeInterval({\n        "end_time": {\5},\n        "start_time": {\4}\n    })\n    filter = f\'metric.type = "\2/\3"\'\n    results = \1.list_time_series(request={"name": project_name, "filter": filter, "interval": interval})',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)

        return code

    def _migrate_apigateway_to_apigee(self, code: str) -> str:
        """Migrate AWS API Gateway to Apigee X"""
        # Store original code for Gemini validation
        original_code = code
        
        # Replace API Gateway imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import apigee_registry_v1', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import apigee_registry_v1', code, flags=re.MULTILINE)

        # Replace API Gateway client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]apigateway[\'\"].*?\)',
            r'\1 = apigee_registry_v1.RegistryClient()',
            code,
            flags=re.DOTALL
        )

        # Replace API creation operations
        code = re.sub(
            r'(\w+)\.create_rest_api\(name=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    parent = f"projects/{project_id}/locations/global"\n    api = apigee_registry_v1.Api(display_name=\2)\n    response = \1.create_api(parent=parent, api=api, api_id=\2.lower().replace(" ", "-"))',
            code
        )

        # Replace get_rest_apis
        code = re.sub(
            r'(\w+)\.get_rest_apis\(\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    parent = f"projects/{project_id}/locations/global"\n    response = \1.list_apis(parent=parent)',
            code
        )

        # Replace deployment operations
        code = re.sub(
            r'(\w+)\.create_deployment\(restApiId=([^,]+),\s*stageName=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    parent = f"projects/{project_id}/locations/global/apis/\2"\n    deployment = apigee_registry_v1.Deployment(name=\3)\n    response = \1.create_deployment(parent=parent, deployment=deployment, deployment_id=\3)',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)

        return code

    def _migrate_eks_to_gke(self, code: str) -> str:
        """Migrate AWS EKS to Google Kubernetes Engine"""
        # Store original code for Gemini validation
        original_code = code
        
        # Replace EKS imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import container_v1', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import container_v1', code, flags=re.MULTILINE)

        # Replace EKS client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]eks[\'\"].*?\)',
            r'\1 = container_v1.ClusterManagerClient()',
            code,
            flags=re.DOTALL
        )

        # Replace cluster operations
        code = re.sub(
            r'(\w+)\.create_cluster\(name=([^,]+),\s*roleArn=([^,]+),\s*resourcesVpcConfig=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    parent = f"projects/{project_id}/locations/{region}"\n    cluster = container_v1.Cluster({\n        "name": \2,\n        "initial_node_count": 1,\n        "node_config": container_v1.NodeConfig({\n            "oauth_scopes": ["https://www.googleapis.com/auth/cloud-platform"]\n        })\n    })\n    request = container_v1.CreateClusterRequest(parent=parent, cluster=cluster)\n    response = \1.create_cluster(request=request)',
            code
        )

        # Replace list_clusters
        code = re.sub(
            r'(\w+)\.list_clusters\(\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    parent = f"projects/{project_id}/locations/-"\n    response = \1.list_clusters(parent=parent)',
            code
        )

        # Replace describe cluster
        code = re.sub(
            r'(\w+)\.describe_cluster\(name=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    name = f"projects/{project_id}/locations/{region}/clusters/\2"\n    response = \1.get_cluster(name=name)',
            code
        )

        # Replace delete cluster
        code = re.sub(
            r'(\w+)\.delete_cluster\(name=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    name = f"projects/{project_id}/locations/{region}/clusters/\2"\n    \1.delete_cluster(name=name)',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)

        return code

    def _migrate_fargate_to_cloudrun(self, code: str) -> str:
        """Migrate AWS Fargate (ECS) to Google Cloud Run"""
        # Store original code for Gemini validation
        original_code = code
        
        # Replace ECS/Fargate imports (ECS manages Fargate tasks)
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import run_v2\nfrom google.cloud.run_v2.types import Service', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import run_v2\nfrom google.cloud.run_v2.types import Service', code, flags=re.MULTILINE)

        # Replace ECS client instantiation (which handles Fargate)
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]ecs[\'\"].*?\)',
            r'\1 = run_v2.ServicesClient()',
            code,
            flags=re.DOTALL
        )

        # Replace ECS run_task which is used for Fargate -> Cloud Run Job
        code = re.sub(
            r'(\w+)\.run_task\(cluster=([^,]+),\s*taskDefinition=([^,]+),\s*count=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    parent = f"projects/{project_id}/locations/{region}"\n    job = run_v2.Job({\n        "template": run_v2.ExecutionTemplate({\n            "containers": [run_v2.Container({"image": os.getenv("GCP_CLOUD_RUN_IMAGE", "IMAGE_URL")})]\n        })\n    })\n    request = run_v2.CreateJobRequest(parent=parent, job=job, job_id=\3)\n    response = \1.create_job(request=request)',
            code
        )

        # Replace ECS register_task_definition -> Cloud Run Service
        code = re.sub(
            r'(\w+)\.register_task_definition\(family=([^,]+),\s*containerDefinitions=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    parent = f"projects/{project_id}/locations/{region}"\n    service = run_v2.Service({\n        "template": run_v2.RevisionTemplate({\n            "containers": [run_v2.Container({"image": os.getenv("GCP_CLOUD_RUN_IMAGE", "IMAGE_URL")})]\n        })\n    })\n    request = run_v2.CreateServiceRequest(parent=parent, service=service, service_id=\2)\n    response = \1.create_service(request=request)',
            code
        )

        # Replace ECS start_task -> Cloud Run Job execution
        code = re.sub(
            r'(\w+)\.start_task\(cluster=([^,]+),\s*taskDefinition=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    name = f"projects/{project_id}/locations/{region}/jobs/\3"\n    request = run_v2.RunJobRequest(name=name)\n    response = \1.run_job(request=request)',
            code
        )

        # Replace list_tasks
        code = re.sub(
            r'(\w+)\.list_tasks\(cluster=([^,\)]+)\)',
            r'import os\n    project_id = os.getenv("GCP_PROJECT_ID", "your-project-id")\n    region = os.getenv("GCP_REGION", "us-central1")\n    parent = f"projects/{project_id}/locations/{region}"\n    response = \1.list_jobs(parent=parent)',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)
        
        # Use Gemini to validate and fix any remaining AWS patterns
        code = self._validate_and_fix_with_gemini(code, original_code)

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
            'import com.google.cloud.storage.Storage;\nimport com.google.cloud.storage.StorageOptions;\nimport com.google.cloud.storage.BlobId;\nimport com.google.cloud.storage.BlobInfo;',
            code
        )
        
        # Replace S3 client type declarations
        code = re.sub(
            r'AmazonS3\s+(\w+)\s*=',
            r'Storage \1 =',
            code
        )
        
        code = re.sub(
            r'private\s+AmazonS3\s+(\w+);',
            r'private Storage \1;',
            code
        )
        
        # Replace S3 client instantiation
        code = re.sub(
            r'AmazonS3ClientBuilder\.standard\(\)[^;]*\.build\(\)',
            'StorageOptions.getDefaultInstance().getService()',
            code
        )
        
        # Replace putObject calls
        code = re.sub(
            r'(\w+)\.putObject\(([^)]+)\)',
            r'\1.create(BlobInfo.newBuilder(BlobId.of(\2)).build())',
            code
        )
        
        return code
    
    def _migrate_lambda_to_cloud_functions(self, code: str) -> str:
        """Migrate AWS Lambda Java code to Google Cloud Functions"""
        # Replace Lambda imports
        code = re.sub(
            r'import com\.amazonaws\.services\.lambda\..*;',
            'import com.google.cloud.functions.HttpFunction;\nimport com.google.cloud.functions.HttpRequest;\nimport com.google.cloud.functions.HttpResponse;',
            code
        )
        
        # Replace RequestHandler interface
        code = re.sub(
            r'implements\s+RequestHandler<[^>]+>',
            'implements HttpFunction',
            code
        )
        
        # Replace handleRequest method - preserve class structure
        code = re.sub(
            r'public\s+([^\(]+)\s+handleRequest\s*\(\s*([^,]+)\s+input\s*,\s*Context\s+context\s*\)',
            r'@Override\n    public void service(HttpRequest request, HttpResponse response) throws Exception',
            code
        )
        
        # Update method body to use request/response
        if 'return Map.of(' in code:
            code = re.sub(
                r'return\s+Map\.of\("statusCode",\s*(\d+),\s*"body",\s*"([^"]+)"\);',
                r'response.setStatusCode(\1);\n        response.getWriter().write("\2");',
                code
            )
        
        return code
    
    def _migrate_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB Java code to Google Cloud Firestore"""
        # Replace DynamoDB imports
        code = re.sub(
            r'import com\.amazonaws\.services\.dynamodbv2\..*;',
            'import com.google.cloud.firestore.Firestore;\nimport com.google.cloud.firestore.FirestoreOptions;\nimport com.google.cloud.firestore.DocumentReference;\nimport com.google.cloud.firestore.WriteBatch;',
            code
        )
        
        # Replace DynamoDB client type declarations
        code = re.sub(
            r'AmazonDynamoDB\s+(\w+)\s*=',
            r'Firestore \1 =',
            code
        )
        
        code = re.sub(
            r'private\s+AmazonDynamoDB\s+(\w+);',
            r'private Firestore \1;',
            code
        )
        
        # Replace DynamoDB client instantiation
        code = re.sub(
            r'AmazonDynamoDBClientBuilder\.standard\(\)[^;]*\.build\(\)',
            'FirestoreOptions.getDefaultInstance().getService()',
            code
        )
        
        # Replace putItem calls
        code = re.sub(
            r'(\w+)\.putItem\(([^)]+)\)',
            r'\1.collection(tableName).document().set(item)',
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
    
    def generate_transformation_recipe(self, source_code: str, target_api: str, language: str, service_type: str, llm_recipe: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a transformation recipe for refactoring code
        
        If llm_recipe is provided, it contains LLM-generated guidance for transformations.
        Otherwise, uses rule-based recipe generation.
        """
        # Base recipe structure
        recipe = {
            'language': language,
            'operation': 'service_migration',
            'service_type': service_type,
            'source_api': f'AWS {service_type.split("_to_")[0].upper()}',
            'target_api': target_api,
            'llm_recipe': llm_recipe,  # Include LLM guidance if available
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
        
        # If LLM recipe is provided, parse it and enhance the transformation steps
        if llm_recipe:
            recipe['llm_guided'] = True
            # The LLM recipe text can be used to inform which specific patterns to look for
            # For now, we include it in the recipe for logging/debugging purposes
            # In a more advanced implementation, we could parse the LLM recipe and extract
            # specific transformation patterns to apply
        
        return recipe
    
    def apply_refactoring(self, source_code: str, language: str, service_type: str, target_api: str = None) -> str:
        """
        Apply refactoring to the source code for the specified service type
        """
        # CRITICAL: Run aggressive AWS cleanup FIRST, before any processing
        if language == 'python':
            source_code = self.ast_engine._aggressive_aws_cleanup(source_code)
        
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
        
        # Generate transformation recipe (llm_recipe parameter can be passed from use case)
        recipe = self.generate_transformation_recipe(
            source_code, 
            target_api, 
            language, 
            service_type,
            llm_recipe=None  # Can be passed from use case if LLM was used
        )
        
        # Apply transformations using AST engine
        # transform_code returns (transformed_code, variable_mapping) tuple
        result = self.ast_engine.transform_code(source_code, language, recipe)
        
        # Handle both tuple and string returns
        if isinstance(result, tuple):
            transformed_code, variable_mapping = result
        else:
            transformed_code = result
        
        # CRITICAL: Run aggressive AWS cleanup AGAIN after transformation
        if language == 'python':
            transformed_code = self.ast_engine._aggressive_aws_cleanup(transformed_code)
        
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