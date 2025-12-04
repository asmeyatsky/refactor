"""
Validate GCP Code Use Case

Architectural Intent:
- Validates that refactored code is correct for Google Cloud Platform
- Checks for AWS patterns, syntax errors, and GCP API correctness
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
        # Note: Bucket= and Key= are checked but only if they appear in AWS context
        # (not in GCP code where they might be legitimate parameter names)
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
        # Only flag create_bucket if it has AWS-specific parameters like Bucket=
        r'(?:s3_client|s3|boto3)\s*\.\s*create_bucket\s*\([^)]*Bucket\s*=',
        r'(?:s3_client|s3|boto3)\s*\.\s*create_bucket\s*\([^)]*CreateBucketConfiguration',
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
        
        if progress_callback:
            progress_callback("Starting validation...", 0.0)
        
        # Step 1: Syntax validation (20%)
        # Skip syntax validation for shell/bash scripts
        is_shell_script = (
            code.strip().startswith('#!') or
            bool(re.search(r'^\s*(az|aws|gcloud|kubectl|docker)\s+', code, re.MULTILINE))
        )
        
        if is_shell_script:
            syntax_valid = True  # Shell scripts don't need Python syntax validation
            if progress_callback:
                progress_callback("Skipping syntax validation for shell script", 20.0)
        else:
            syntax_valid = self._validate_syntax(code, language)
            if progress_callback:
                progress_callback("Syntax validation complete", 20.0)
        
        if not syntax_valid:
            errors.append("Code contains syntax errors")
        
        # Step 2: Clean code before checking for AWS patterns (35%)
        # Run aggressive cleanup to remove any remaining AWS patterns
        if language == 'python':
            try:
                from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
                cleanup_engine = ExtendedASTTransformationEngine()
                if hasattr(cleanup_engine, '_aggressive_aws_cleanup'):
                    code = cleanup_engine._aggressive_aws_cleanup(code)
            except Exception:
                pass  # Continue with original code if cleanup fails
        
        if progress_callback:
            progress_callback("Cleanup complete, checking for AWS patterns", 37.5)
        
        # Step 2: Check for AWS patterns (40%)
        aws_patterns_found = self._detect_aws_patterns(code, language)
        if progress_callback:
            progress_callback(f"Found {len(aws_patterns_found)} AWS patterns", 40.0)
        
        if aws_patterns_found:
            errors.append(f"Found {len(aws_patterns_found)} AWS patterns in code")
            warnings.append("Code may not be fully migrated to GCP")
        
        # Step 3: Check GCP API correctness (60%)
        gcp_api_correct = self._validate_gcp_apis(code, language)
        if progress_callback:
            progress_callback("GCP API validation complete", 80.0)
        
        # Only warn about GCP API if:
        # 1. We found AWS patterns (meaning migration was attempted)
        # 2. AND GCP APIs are not detected
        # This prevents false positives for code that doesn't use cloud services
        if not gcp_api_correct and aws_patterns_found:
            # Check if code actually uses cloud services (not just simple Python code)
            has_cloud_operations = any(pattern in code.lower() for pattern in [
                'client', 'bucket', 'blob', 'collection', 'document', 'topic', 
                'subscription', 'function', 'service', 'instance', 'cluster'
            ])
            if has_cloud_operations:
                warnings.append("GCP API usage may be incorrect or incomplete - verify GCP SDK imports and client initialization")
        
        # Step 4: Advanced LLM validation if available (100%)
        if self.llm_provider and aws_patterns_found:
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
            azure_patterns_found=[],  # Always empty - Azure not supported
            syntax_valid=syntax_valid,
            gcp_api_correct=gcp_api_correct,
            validation_details={
                'total_patterns_found': len(aws_patterns_found),
                'has_aws_patterns': len(aws_patterns_found) > 0,
                'has_azure_patterns': False,
                'language': language
            }
        )
    
    def _validate_syntax(self, code: str, language: str) -> bool:
        """Validate code syntax"""
        if not code or not code.strip():
            # Empty code is syntactically valid (though may not be useful)
            return True
        
        # Check if code is shell/bash script - skip Python syntax validation
        is_shell_script = (
            code.strip().startswith('#!') or
            bool(re.search(r'^\s*(az|aws|gcloud|kubectl|docker)\s+', code, re.MULTILINE))
        )
        
        if is_shell_script:
            logger.info("Detected shell/bash script - skipping Python syntax validation")
            return True  # Shell scripts are valid in their own context
            
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
            elif language in ['javascript', 'js', 'nodejs', 'node']:
                # Basic JavaScript syntax check
                # Check for balanced braces and parentheses
                open_braces = code.count('{')
                close_braces = code.count('}')
                open_parens = code.count('(')
                close_parens = code.count(')')
                if open_braces != close_braces or open_parens != close_parens:
                    return False
                return True
            elif language in ['go', 'golang']:
                # Basic Go syntax check
                # Check for balanced braces and package declaration
                if 'package' not in code:
                    return False
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
        import re
        found_patterns = []
        code_lower = code.lower()
        
        # Check for Bucket= only if it's in AWS context (not GCP)
        # GCP code should NOT have Bucket= parameters - they use positional args
        if 'Bucket=' in code:
            # Check if Bucket= appears in actual code (not just comments/strings)
            # Remove comments and strings first
            code_clean = self._remove_comments_and_strings(code, language)
            if 'Bucket=' in code_clean:
                # Only flag if it's NOT in GCP context (storage.Client, google.cloud)
                # Check if there's GCP context nearby
                bucket_positions = [m.start() for m in re.finditer(r'Bucket\s*=', code_clean)]
                for pos in bucket_positions:
                    # Check context before this position
                    context_before = code_clean[max(0, pos-200):pos]
                    # If we see GCP patterns nearby, it might be a false positive
                    if 'storage.Client' not in context_before and 'google.cloud' not in context_before:
                        found_patterns.append('Bucket=')
                        break
        
        # Check for create_bucket() only if it has AWS-specific parameters
        if 'create_bucket(' in code:
            code_clean = self._remove_comments_and_strings(code, language)
            # Only flag if it has Bucket= parameter or is called on AWS client
            if re.search(r'(?:s3_client|s3|boto3)\s*\.\s*create_bucket\s*\([^)]*Bucket\s*=', code_clean):
                found_patterns.append('create_bucket()')
            elif re.search(r'\w+\s*\.\s*create_bucket\s*\([^)]*Bucket\s*=', code_clean):
                # Check if it's GCP code - if storage.Client is nearby, it's OK
                matches = list(re.finditer(r'\w+\s*\.\s*create_bucket\s*\([^)]*Bucket\s*=', code_clean))
                for match in matches:
                    context_before = code_clean[max(0, match.start()-200):match.start()]
                    if 'storage.Client' not in context_before and 'google.cloud' not in context_before:
                        found_patterns.append('create_bucket()')
                        break
        
        # Use language-specific patterns (excluding Bucket= and create_bucket() which we handle above)
        patterns_to_check = [p for p in self.AWS_PATTERNS if p not in ['Bucket=', 'create_bucket()']]
        if language == 'java':
            # Add Java-specific AWS patterns
            java_patterns = [
                'com.amazonaws',
                'AmazonS3',
                'AmazonDynamoDB',
                'AmazonSQS',
                'AmazonSNS',
                'S3Client',
                'DynamoDBClient',
                'SQSClient',
                'SNSClient',
                'AmazonS3ClientBuilder',
                'S3ClientBuilder',
            ]
            patterns_to_check = list(self.AWS_PATTERNS) + java_patterns
        elif language in ['csharp', 'c#']:
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
        elif language in ['javascript', 'js', 'nodejs', 'node']:
            # Add JavaScript/Node.js-specific AWS patterns
            javascript_patterns = [
                'aws-sdk',
                '@aws-sdk',
                'AWS.S3',
                'AWS.DynamoDB',
                'AWS.Lambda',
                'AWS.SQS',
                'AWS.SNS',
                'S3Client',
                'DynamoDBClient',
                'LambdaClient',
                'SQSClient',
                'SNSClient',
            ]
            patterns_to_check = list(self.AWS_PATTERNS) + javascript_patterns
        elif language in ['go', 'golang']:
            # Add Go-specific AWS patterns
            go_patterns = [
                'github.com/aws/aws-sdk-go',
                'github.com/aws/aws-sdk-go-v2',
                's3.New',
                'dynamodb.New',
                'lambda.New',
                'sqs.New',
                'sns.New',
                's3iface',
                'dynamodbiface',
            ]
            patterns_to_check = list(self.AWS_PATTERNS) + go_patterns
        
        # Check literal patterns - be more precise to avoid false positives
        # First, remove comments and string literals to avoid false positives
        code_without_comments = self._remove_comments_and_strings(code, language)
        code_without_comments_lower = code_without_comments.lower()
        
        for pattern in patterns_to_check:
            pattern_lower = pattern.lower()
            # Only check in code without comments/strings
            if pattern_lower in code_without_comments_lower:
                # Skip common false positives that might appear in GCP code
                # These patterns are too generic and might match legitimate GCP code
                false_positives = [
                    'region=',     # Too generic - GCP uses regions too
                    'functionname=',  # Too generic
                    'engine',      # Too generic - Cloud SQL uses engine too
                ]
                
                # Additional check: if pattern only appears in regex patterns (r'...'), skip it
                # This catches patterns like CreateBucketConfiguration in regex strings
                pattern_in_regex_only = False
                if language == 'python':
                    # Check if pattern only appears inside regex strings (r'...' or r"...")
                    regex_pattern = r"r['\"].*?" + re.escape(pattern) + r".*?['\"]"
                    if re.search(regex_pattern, code, re.IGNORECASE | re.DOTALL):
                        # Check if it also appears outside regex strings
                        # Remove all regex strings and check if pattern still exists
                        code_no_regex = re.sub(r"r['\"].*?['\"]", '', code, flags=re.DOTALL)
                        if pattern_lower not in code_no_regex.lower():
                            pattern_in_regex_only = True
                
                # Only add if not a false positive and not only in regex patterns
                if pattern_lower not in false_positives and not pattern_in_regex_only:
                    found_patterns.append(pattern)
        
        # Check regex patterns - these are more precise
        # Use cleaned code (without comments/strings) for regex matching
        for pattern in self.AWS_METHOD_PATTERNS:
                matches = re.findall(pattern, code_without_comments, re.IGNORECASE)
                if matches:
                    # For upload_file, download_file, etc. - only flag if called on AWS clients
                    # Don't flag if called on GCP clients (storage_client, bucket, blob, etc.)
                    if pattern in [r'\w+\s*\.\s*upload_file\s*\(', r'\w+\s*\.\s*download_file\s*\(']:
                        # Check if it's called on AWS client (s3_client, s3, etc.) vs GCP client
                        aws_client_pattern = r'(s3_client|s3|boto3\.client\([\'"]s3)'
                        gcp_client_pattern = r'(storage_client|bucket|blob|storage\.Client)'
                        is_aws_call = False
                        for match in matches:
                            # Find the context around the match in cleaned code
                            match_pos = code_without_comments_lower.find(match.lower())
                            if match_pos >= 0:
                                # Check 50 chars before the match for client name
                                context_start = max(0, match_pos - 50)
                                context = code_without_comments[context_start:match_pos + len(match)]
                                if re.search(aws_client_pattern, context, re.IGNORECASE):
                                    is_aws_call = True
                                    break
                                elif re.search(gcp_client_pattern, context, re.IGNORECASE):
                                    # It's a GCP call, skip it
                                    continue
                        if not is_aws_call:
                            continue  # Skip this pattern - might be GCP code
                    
                    # Extract meaningful pattern name from regex
                    pattern_name = self._extract_pattern_name(pattern, matches[0] if matches else None)
                    if pattern_name and pattern_name not in found_patterns:
                        found_patterns.append(pattern_name)
        
        return list(set(found_patterns))  # Remove duplicates
    
    def _remove_comments_and_strings(self, code: str, language: str) -> str:
        """Remove comments and string literals from code to avoid false positives"""
        if language == 'python':
            import tokenize
            import io
            
            try:
                # Use tokenize to remove comments and strings - most reliable method
                tokens = []
                for token in tokenize.generate_tokens(io.StringIO(code).readline):
                    token_type = token[0]
                    token_string = token[1]
                    
                    # Skip comments and ALL string literals (including regex patterns)
                    if token_type not in (tokenize.COMMENT, tokenize.STRING):
                        tokens.append(token_string)
                    else:
                        # Replace with spaces to preserve line structure
                        tokens.append(' ' * len(token_string))
                
                return ''.join(tokens)
            except Exception:
                # Fallback: comprehensive regex-based removal
                # Remove single-line comments (but not in strings)
                lines = code.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Remove everything after # (but check if # is in a string)
                    if '#' in line:
                        comment_pos = line.find('#')
                        # Check if # is in a string
                        in_string = False
                        quote_char = None
                        for i, char in enumerate(line[:comment_pos]):
                            if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                                if quote_char is None:
                                    quote_char = char
                                    in_string = True
                                elif char == quote_char:
                                    in_string = False
                                    quote_char = None
                        if not in_string:
                            line = line[:comment_pos]
                    cleaned_lines.append(line)
                
                # Remove multi-line strings (docstrings)
                code_no_comments = '\n'.join(cleaned_lines)
                # Remove triple-quoted strings (docstrings)
                code_no_comments = re.sub(r'""".*?"""', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r"'''.*?'''", '', code_no_comments, flags=re.DOTALL)
                
                # Remove ALL string literals including regex patterns (r'...', r"...", '...', "...")
                # Handle raw strings (r'...', r"...")
                code_no_comments = re.sub(r"r'[^']*'", '', code_no_comments)
                code_no_comments = re.sub(r'r"[^"]*"', '', code_no_comments)
                # Handle regular strings
                code_no_comments = re.sub(r"'[^']*'", '', code_no_comments)
                code_no_comments = re.sub(r'"[^"]*"', '', code_no_comments)
                # Handle triple-quoted strings again (in case they weren't caught)
                code_no_comments = re.sub(r'r""".*?"""', '', code_no_comments, flags=re.DOTALL)
                code_no_comments = re.sub(r"r'''.*?'''", '', code_no_comments, flags=re.DOTALL)
                
                return code_no_comments
        elif language == 'java':
            # Remove Java comments
            # Remove single-line comments
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            # Remove multi-line comments
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            # Remove string literals
            code = re.sub(r'"[^"]*"', '', code)
            code = re.sub(r"'[^']*'", '', code)
            return code
        elif language in ['csharp', 'c#']:
            # Remove C# comments
            # Remove single-line comments
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            # Remove multi-line comments
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            # Remove string literals
            code = re.sub(r'@"[^"]*"', '', code)  # Verbatim strings
            code = re.sub(r'"[^"]*"', '', code)   # Regular strings
            code = re.sub(r"'[^']*'", '', code)   # Character literals
            return code
        elif language in ['javascript', 'js', 'nodejs', 'node']:
            # Remove JavaScript comments
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            # Remove string literals
            code = re.sub(r'"[^"]*"', '', code)
            code = re.sub(r"'[^']*'", '', code)
            code = re.sub(r'`[^`]*`', '', code)  # Template literals
            return code
        elif language in ['go', 'golang']:
            # Remove Go comments
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            # Remove string literals
            code = re.sub(r'`[^`]*`', '', code)  # Raw strings
            code = re.sub(r'"[^"]*"', '', code)  # Regular strings
            code = re.sub(r"'[^']*'", '', code)  # Runes
            return code
        
        # Default: just remove basic comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def _extract_pattern_name(self, regex_pattern: str, match: str = None) -> str:
        """Extract a human-readable pattern name from regex"""
        # Map regex patterns to readable names
        pattern_map = {
            r'\bboto3\s*\.\s*(client|resource)\s*\(': 'boto3.client() or boto3.resource()',
            # Removed: r'\bs3\s*\.\s*\w+': 'S3 operation' - too generic, causes false positives
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
            
            prompt = f"""Analyze this {language} code that was refactored from AWS to Google Cloud Platform.

Code:
```{language}
{code}
```

Check for:
1. Any remaining AWS patterns
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
