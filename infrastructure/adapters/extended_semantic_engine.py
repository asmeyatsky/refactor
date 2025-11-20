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
        Ensures the output is syntactically correct.
        
        Returns:
            tuple: (transformed_code, variable_mapping) where variable_mapping is a dict
                   mapping old variable names to new variable names
        """
        if language not in self.transformers:
            raise ValueError(f"Unsupported language: {language}")

        transformer = self.transformers[language]
        transformed_code = transformer.transform(code, transformation_recipe)
        
        # Validate syntax for Python code
        if language == 'python':
            transformed_code = self._validate_and_fix_syntax(transformed_code, original_code=code)
        
        # Get variable mapping if available
        variable_mapping = {}
        if hasattr(transformer, '_variable_mappings'):
            code_id = id(code)
            variable_mapping = transformer._variable_mappings.get(code_id, {})
        
        return transformed_code, variable_mapping
    
    def _validate_and_fix_syntax(self, code: str, original_code: str = None) -> str:
        """
        Validate Python syntax and attempt to fix common issues.
        Returns syntactically correct code or raises SyntaxError.
        """
        import ast
        import logging
        logger = logging.getLogger(__name__)
        
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
                # If we can't fix it, log the error and return original code
                # This ensures we never return invalid code
                logger.error(f"Transformed code has syntax errors that couldn't be fixed: {e}")
                logger.debug(f"Invalid code:\n{code[:1000]}")
                
                # Return original code as fallback to ensure we always return valid code
                if original_code:
                    logger.warning("Returning original code due to transformation syntax errors")
                    return original_code
                else:
                    # If no original code, raise error
                    raise SyntaxError(f"Transformed code is invalid and cannot be fixed: {e}")
    
    def _attempt_syntax_fix(self, code: str, syntax_error: SyntaxError) -> str:
        """
        Attempt to fix common syntax errors in transformed code.
        """
        fixed = code
        
        # Fix common indentation issues
        # Remove leading spaces that cause indentation errors
        lines = fixed.split('\n')
        fixed_lines = []
        for line in lines:
            # If line has inconsistent indentation, try to fix it
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # This might be a line that should be indented
                # For now, we'll leave it as is and let AST catch it
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        fixed = '\n'.join(fixed_lines)
        
        # Fix double assignments (e.g., "response = bucket = ...")
        fixed = re.sub(r'(\w+)\s*=\s*(\w+)\s*=\s*', r'\1 = ', fixed)
        
        # Fix malformed statements
        # Remove lines that are just indented without proper context
        lines = fixed.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            # Skip lines that are incorrectly indented standalone statements
            if line.strip() and line.startswith('    ') and not line.strip().startswith('#'):
                # Check if previous line ends with colon (should be indented)
                if i > 0 and lines[i-1].strip().endswith(':'):
                    fixed_lines.append(line)
                elif i > 0 and not lines[i-1].strip().endswith(':'):
                    # This line shouldn't be indented - fix it
                    fixed_lines.append(line.lstrip())
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        fixed = '\n'.join(fixed_lines)
        
        return fixed


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
        
        # Check for each service type and apply transformations
        if 'boto3' in result_code and 's3' in result_code.lower():
            result_code, var_mapping = self._migrate_s3_to_gcs(result_code)
            # Store variable mapping
            if not hasattr(self, '_variable_mappings'):
                self._variable_mappings = {}
            self._variable_mappings[id(result_code)] = var_mapping
        
        if 'boto3' in result_code and 'lambda' in result_code.lower():
            result_code, var_mapping = self._migrate_lambda_to_cloud_functions(result_code)
            # Store variable mapping
            if not hasattr(self, '_variable_mappings'):
                self._variable_mappings = {}
            self._variable_mappings[id(result_code)] = var_mapping
        
        if 'boto3' in result_code and 'dynamodb' in result_code.lower():
            result_code = self._migrate_dynamodb_to_firestore(result_code)
        
        if 'boto3' in result_code and 'sqs' in result_code.lower():
            result_code = self._migrate_sqs_to_pubsub(result_code)
        
        if 'boto3' in result_code and 'sns' in result_code.lower():
            result_code = self._migrate_sns_to_pubsub(result_code)
        
        if 'boto3' in result_code and 'rds' in result_code.lower():
            result_code = self._migrate_rds_to_cloud_sql(result_code)
        
        if 'boto3' in result_code and 'cloudwatch' in result_code.lower():
            result_code = self._migrate_cloudwatch_to_monitoring(result_code)

        if 'boto3' in result_code and 'apigateway' in result_code.lower():
            result_code = self._migrate_apigateway_to_apigee(result_code)

        if 'boto3' in result_code and 'eks' in result_code.lower():
            result_code = self._migrate_eks_to_gke(result_code)

        if 'boto3' in result_code and ('ecs' in result_code.lower() or 'fargate' in result_code.lower()):
            result_code = self._migrate_fargate_to_cloudrun(result_code)

        return result_code
    
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
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]s3[\'\"].*?\)',
            r'gcs_client = storage.Client()  # Use a better name for the GCS client',
            code,
            flags=re.DOTALL
        )
        
        # Also replace common S3 variable names (do this after specific replacement)
        code = re.sub(r'\bs3_client\b', 'gcs_client', code)
        # Replace standalone 's3' variable when used as a client (followed by dot)
        # Match: s3.upload_file, s3.put_object, etc. but not 's3' in strings
        code = re.sub(r'\bs3\b(?=\s*\.)', 'gcs_client', code)
        
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
        # Client var should already be gcs_client at this point
        def replace_upload(match):
            return f'### 🚀 Upload file to GCS\nbucket = gcs_client.bucket(bucket_name)\nblob = bucket.blob(remote_file_name)\nblob.upload_from_filename(local_upload_file)\nprint(f"File {{local_upload_file}} uploaded to gs://{{bucket_name}}/{{remote_file_name}}")'
        code = re.sub(
            r'(\w+)\.upload_file\([\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"],\s*[\'\"]([^\'\"]+)[\'\"]\)',
            replace_upload,
            code
        )
        
        # Replace S3 download_file -> GCS download_to_filename with improved structure
        # Pattern: s3_client.download_file('bucket-name', 'remote_file.txt', 'local_file.txt')
        def replace_download(match):
            return f'# ---\n\n### 📥 Download file from GCS\n# The bucket and blob objects can be reused, but shown for clarity\nbucket = gcs_client.bucket(bucket_name)\nblob = bucket.blob(remote_file_name)\nblob.download_to_filename(local_download_file)\nprint(f"File gs://{{bucket_name}}/{{remote_file_name}} downloaded to {{local_download_file}}")'
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
            return f'# ---\n\n### 📥 Download file from GCS\nbucket = gcs_client.bucket(bucket_name)\nblob = bucket.blob(remote_file_name)\ncontent = blob.download_as_text()\nprint(f"File gs://{{bucket_name}}/{{remote_file_name}} downloaded")'
        # Match get_object with optional additional parameters
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
        
        # Handle response['Body'].read() pattern - replace with blob content
        code = re.sub(
            r'(\w+)\[\'Body\'\]\.read\(\)',
            r'content',
            code
        )
        code = re.sub(
            r'(\w+)\["Body"\]\.read\(\)',
            r'content',
            code
        )
        
        # Replace S3 delete_object -> GCS delete with improved structure
        def replace_delete_object(match):
            return f'# ---\n\n### 🗑️ Delete object from GCS\nbucket = gcs_client.bucket(bucket_name)\nblob = bucket.blob(remote_file_name)\nblob.delete()\nprint(f"Object gs://{{bucket_name}}/{{remote_file_name}} deleted")'
        code = re.sub(
            r'(\w+)\.delete_object\(Bucket=([^,]+),\s*Key=([^,\)]+)\)',
            replace_delete_object,
            code
        )
        
        # Replace S3 list_objects_v2 -> GCS list_blobs with improved structure
        # Pattern: response = s3_client.list_objects_v2(Bucket='my-bucket')
        # Should become: blobs = gcs_client.list_blobs(bucket_name)
        def replace_list_objects_v2(match):
            # Client var should already be gcs_client at this point
            return f'# ---\n\n### 📜 List objects (Blobs) in bucket\nprint(f\"\\nObjects in bucket {{bucket_name}}:\")\n# The list_blobs() method returns an iterable of Blob objects\nblobs = gcs_client.list_blobs(bucket_name)'
        
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
        
        # Replace S3 create_bucket -> GCS create_bucket with improved structure
        def replace_create_bucket(match):
            return f'### 🆕 Create bucket in GCS\nbucket = gcs_client.create_bucket(bucket_name)\nprint(f"Bucket gs://{{bucket_name}} created")'
        code = re.sub(
            r'(\w+)\.create_bucket\(Bucket=([^,]+)(?:,\s*CreateBucketConfiguration=[^\)]+)?\)',
            replace_create_bucket,
            code
        )
        code = re.sub(
            r'(\w+)\.create_bucket\(Bucket=([^,\)]+)\)',
            replace_create_bucket,
            code
        )
        
        # Replace S3 delete_bucket -> GCS delete_bucket with improved structure
        def replace_delete_bucket(match):
            return f'# ---\n\n### 🗑️ Delete bucket from GCS\nbucket = gcs_client.bucket(bucket_name)\nbucket.delete()\nprint(f"Bucket gs://{{bucket_name}} deleted")'
        code = re.sub(
            r'(\w+)\.delete_bucket\(Bucket=([^,\)]+)\)',
            replace_delete_bucket,
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
        
        return code, variable_mapping
    
    def _add_exception_handling(self, code: str) -> str:
        """Add exception handling transformations for all AWS services"""
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
        
        # Replace Lambda function handler patterns
        # Pattern: def lambda_handler(event, context):
        def replace_lambda_handler(match):
            return '@functions_framework.http\ndef function_handler(request):\n    """\n    Google Cloud Function HTTP handler.\n    Args:\n        request (flask.Request): The request object.\n    Returns:\n        The response text or JSON.\n    """\n    request_json = request.get_json(silent=True)\n    # Convert AWS Lambda event to GCF request format\n    event = request_json if request_json else {}\n    context = {}  # GCF doesn\'t use context object like Lambda\n    # Original handler code follows:'
        
        code = re.sub(
            r'def\s+lambda_handler\s*\(\s*event\s*,\s*context\s*\)\s*:',
            replace_lambda_handler,
            code,
            flags=re.IGNORECASE
        )
        
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
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport requests\n# For HTTP-triggered functions, use the function URL\nfunction_url = f"https://{{GCP_REGION}}-{{GCP_PROJECT_ID}}.cloudfunctions.net/{function_name}"\n{var_name} = requests.post(function_url, json={payload_str})\nresult = {var_name}.json() if {var_name}.headers.get(\'content-type\', \'\').startswith(\'application/json\') else {var_name}.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
        def replace_invoke_direct(match):
            # Pattern: client.invoke(...)
            client_var = match.group(1)
            function_name = match.group(2).strip('\'"')
            invocation_type = match.group(3).strip('\'"') if match.group(3) else 'RequestResponse'
            payload = match.group(4)
            payload_str = payload.strip()
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport requests\n# For HTTP-triggered functions, use the function URL\nfunction_url = f"https://{{GCP_REGION}}-{{GCP_PROJECT_ID}}.cloudfunctions.net/{function_name}"\nresponse = requests.post(function_url, json={payload_str})\nresult = response.json() if response.headers.get(\'content-type\', \'\').startswith(\'application/json\') else response.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
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
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport requests\n# For HTTP-triggered functions, use the function URL\nfunction_url = f"https://{{GCP_REGION}}-{{GCP_PROJECT_ID}}.cloudfunctions.net/{function_name}"\n{var_name} = requests.post(function_url, json={payload})\nresult = {var_name}.json() if {var_name}.headers.get(\'content-type\', \'\').startswith(\'application/json\') else {var_name}.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
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
            return f'### 🌐 Invoke Cloud Function via HTTP\nimport requests\n# For HTTP-triggered functions, use the function URL\nfunction_url = f"https://{{GCP_REGION}}-{{GCP_PROJECT_ID}}.cloudfunctions.net/{function_name}"\nresponse = requests.post(function_url, json={payload})\nresult = response.json() if response.headers.get(\'content-type\', \'\').startswith(\'application/json\') else response.text\nprint(f"Function {function_name} invoked: {{result}}")'
        
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
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        return code, variable_mapping
    
    def _migrate_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB to Google Cloud Firestore"""
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
    
    def _migrate_sqs_to_pubsub(self, code: str) -> str:
        """Migrate AWS SQS to Google Cloud Pub/Sub"""
        # Replace SQS imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        
        # Replace SQS client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]sqs[\'\"].*?\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code,
            flags=re.DOTALL
        )
        
        # Replace SQS send_message -> Pub/Sub publish
        code = re.sub(
            r'(\w+)\.send_message\(QueueUrl=([^,]+),\s*MessageBody=([^,\)]+)\)',
            rf'topic_path = \1.topic_path("{self.gcp_project_id}", "topic-name")\n    future = \1.publish(topic_path, \3.encode("utf-8"))',
            code
        )
        
        # Replace receive_message -> Pub/Sub pull
        code = re.sub(
            r'(\w+)\.receive_message\(QueueUrl=([^,\)]+)\)',
            rf'subscriber = pubsub_v1.SubscriberClient()\n    subscription_path = subscriber.subscription_path("{self.gcp_project_id}", "subscription-name")\n    response = subscriber.pull(request={{"subscription": subscription_path, "max_messages": 1}})',
            code
        )
        
        # Replace delete_message -> Pub/Sub acknowledge
        code = re.sub(
            r'(\w+)\.delete_message\(QueueUrl=([^,]+),\s*ReceiptHandle=([^,\)]+)\)',
            r'subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": [\3]})',
            code
        )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        return code
    
    def _migrate_sns_to_pubsub(self, code: str) -> str:
        """Migrate AWS SNS to Google Cloud Pub/Sub"""
        # Replace SNS imports
        code = re.sub(r'^import boto3\s*$', 'from google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        code = re.sub(r'^from boto3', 'from google.cloud import pubsub_v1', code, flags=re.MULTILINE)
        
        # Replace SNS client instantiation
        code = re.sub(
            r'(\w+)\s*=\s*boto3\.client\([\'\"]sns[\'\"].*?\)',
            r'\1 = pubsub_v1.PublisherClient()',
            code,
            flags=re.DOTALL
        )
        
        # Replace SNS publish -> Pub/Sub publish
        code = re.sub(
            r'(\w+)\.publish\(TopicArn=([^,]+),\s*Message=([^,\)]+)\)',
            rf'topic_path = \1.topic_path("{self.gcp_project_id}", "topic-name")\n    future = \1.publish(topic_path, \3.encode("utf-8"))',
            code
        )
        
        # Replace create_topic
        code = re.sub(
            r'(\w+)\.create_topic\(Name=([^,\)]+)\)',
            rf'topic_path = \1.topic_path("{self.gcp_project_id}", \2)\n    topic = \1.create_topic(request={{"name": topic_path}})',
            code
        )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        return code
    
    def _migrate_rds_to_cloud_sql(self, code: str) -> str:
        """Migrate AWS RDS to Google Cloud SQL"""
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
                rf'connector = Connector()\n    connection = connector.connect(\n        "{self.gcp_project_id}:{self.gcp_region}:INSTANCE",\n        "pymysql",\n        user=\2,\n        password=\3,\n        db=\4\n    )',
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
                rf'connector = Connector()\n    connection = connector.connect(\n        "{self.gcp_project_id}:{self.gcp_region}:INSTANCE",\n        "psycopg2",\n        user=\2,\n        password=\3,\n        db=\4\n    )',
                code
            )
        
        # Add exception handling
        code = self._add_exception_handling(code)
        
        return code

    def _migrate_cloudwatch_to_monitoring(self, code: str) -> str:
        """Migrate AWS CloudWatch to Google Cloud Monitoring"""
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
            rf'project_name = f"projects/{self.gcp_project_id}"\n    series = monitoring_v3.TimeSeries()\n    series.metric.type = "custom.googleapis.com/metric"\n    # Add metric data points',
            code
        )
        
        # Replace get_metric_statistics
        code = re.sub(
            r'(\w+)\.get_metric_statistics\(Namespace=([^,]+),\s*MetricName=([^,]+),\s*StartTime=([^,]+),\s*EndTime=([^,]+),\s*Period=([^,]+),\s*Statistics=\[([^,\)]+)\]\)',
            rf'project_name = f"projects/{self.gcp_project_id}"\n    interval = monitoring_v3.TimeInterval({{\n        "end_time": {{\5}},\n        "start_time": {{\4}}\n    }})\n    filter = f\'metric.type = "\2/\3"\'\n    results = \1.list_time_series(request={{"name": project_name, "filter": filter, "interval": interval}})',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)

        return code

    def _migrate_apigateway_to_apigee(self, code: str) -> str:
        """Migrate AWS API Gateway to Apigee X"""
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
            rf'parent = f"projects/{self.gcp_project_id}/locations/global"\n    api = apigee_registry_v1.Api(display_name=\2)\n    response = \1.create_api(parent=parent, api=api, api_id=\2.lower().replace(" ", "-"))',
            code
        )

        # Replace get_rest_apis
        code = re.sub(
            r'(\w+)\.get_rest_apis\(\)',
            rf'parent = f"projects/{self.gcp_project_id}/locations/global"\n    response = \1.list_apis(parent=parent)',
            code
        )

        # Replace deployment operations
        code = re.sub(
            r'(\w+)\.create_deployment\(restApiId=([^,]+),\s*stageName=([^,\)]+)\)',
            rf'parent = f"projects/{self.gcp_project_id}/locations/global/apis/\2"\n    deployment = apigee_registry_v1.Deployment(name=\3)\n    response = \1.create_deployment(parent=parent, deployment=deployment, deployment_id=\3)',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)

        return code

    def _migrate_eks_to_gke(self, code: str) -> str:
        """Migrate AWS EKS to Google Kubernetes Engine"""
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
            rf'parent = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}"\n    cluster = container_v1.Cluster({{\n        "name": \2,\n        "initial_node_count": 1,\n        "node_config": container_v1.NodeConfig({{\n            "oauth_scopes": ["https://www.googleapis.com/auth/cloud-platform"]\n        }})\n    }})\n    request = container_v1.CreateClusterRequest(parent=parent, cluster=cluster)\n    response = \1.create_cluster(request=request)',
            code
        )

        # Replace list_clusters
        code = re.sub(
            r'(\w+)\.list_clusters\(\)',
            rf'parent = f"projects/{self.gcp_project_id}/locations/-"\n    response = \1.list_clusters(parent=parent)',
            code
        )

        # Replace describe cluster
        code = re.sub(
            r'(\w+)\.describe_cluster\(name=([^,\)]+)\)',
            rf'name = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}/clusters/\2"\n    response = \1.get_cluster(name=name)',
            code
        )

        # Replace delete cluster
        code = re.sub(
            r'(\w+)\.delete_cluster\(name=([^,\)]+)\)',
            rf'name = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}/clusters/\2"\n    \1.delete_cluster(name=name)',
            code
        )

        # Add exception handling
        self._add_exception_handling(code)

        return code

    def _migrate_fargate_to_cloudrun(self, code: str) -> str:
        """Migrate AWS Fargate (ECS) to Google Cloud Run"""
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
            rf'parent = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}"\n    job = run_v2.Job({{\n        "template": run_v2.ExecutionTemplate({{\n            "containers": [run_v2.Container({{"image": "IMAGE_URL"}})]\n        }})\n    }})\n    request = run_v2.CreateJobRequest(parent=parent, job=job, job_id=\3)\n    response = \1.create_job(request=request)',
            code
        )

        # Replace ECS register_task_definition -> Cloud Run Service
        code = re.sub(
            r'(\w+)\.register_task_definition\(family=([^,]+),\s*containerDefinitions=([^,\)]+)\)',
            rf'parent = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}"\n    service = run_v2.Service({{\n        "template": run_v2.RevisionTemplate({{\n            "containers": [run_v2.Container({{"image": "IMAGE_URL"}})]\n        }})\n    }})\n    request = run_v2.CreateServiceRequest(parent=parent, service=service, service_id=\2)\n    response = \1.create_service(request=request)',
            code
        )

        # Replace ECS start_task -> Cloud Run Job execution
        code = re.sub(
            r'(\w+)\.start_task\(cluster=([^,]+),\s*taskDefinition=([^,\)]+)\)',
            rf'name = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}/jobs/\3"\n    request = run_v2.RunJobRequest(name=name)\n    response = \1.run_job(request=request)',
            code
        )

        # Replace list_tasks
        code = re.sub(
            r'(\w+)\.list_tasks\(cluster=([^,\)]+)\)',
            rf'parent = f"projects/{self.gcp_project_id}/locations/{self.gcp_region}"\n    response = \1.list_jobs(parent=parent)',
            code
        )

        # Add exception handling
        code = self._add_exception_handling(code)

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
            'import com.google.cloud.storage.*;',
            code
        )
        
        # Replace S3 client instantiation
        code = re.sub(
            r'S3Client\.builder\(\).build\(\)',
            'StorageOptions.getDefaultInstance().getService()',
            code
        )
        
        return code
    
    def _migrate_lambda_to_cloud_functions(self, code: str) -> str:
        """Migrate AWS Lambda Java code to Google Cloud Functions"""
        # Replace Lambda imports
        code = re.sub(
            r'import com\.amazonaws\.services\.lambda\..*;',
            'import com.google.cloud.functions.*;',
            code
        )
        
        return code
    
    def _migrate_dynamodb_to_firestore(self, code: str) -> str:
        """Migrate AWS DynamoDB Java code to Google Cloud Firestore"""
        # Replace DynamoDB imports
        code = re.sub(
            r'import com\.amazonaws\.services\.dynamodbv2\..*;',
            'import com.google.cloud.firestore.*;',
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
        transformed_code = self.ast_engine.transform_code(source_code, language, recipe)
        
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