"""
Infrastructure Layer - Adapters

Architectural Intent:
- Implement the interfaces defined in the domain layer
- Handle integration with external services like LLMs, AST tools, etc.
- Provide concrete implementations for code analysis, LLM calls, etc.
"""

import re
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from domain.entities.codebase import Codebase
from domain.entities.refactoring_plan import RefactoringTask
from domain.ports import CodeAnalyzerPort, LLMProviderPort, ASTTransformationPort, TestRunnerPort


class CodeAnalyzerAdapter(CodeAnalyzerPort):
    """Implementation of CodeAnalyzerPort using AST and regex for code analysis"""
    
    def identify_aws_s3_usage(self, codebase: Codebase) -> List[str]:
        """Identify all files containing AWS S3 usage"""
        s3_files = []
        
        for file_path in codebase.files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    
                    # Look for common AWS S3 patterns
                    s3_patterns = [
                        r'import.*boto3',  # Python
                        r'from.*boto3',    # Python
                        r'import.*aws.*s3',  # Python/Java
                        r'import.*S3',      # Any S3 import
                        r'client\..*s3',    # S3 client usage
                        r's3\..*bucket',    # S3 bucket operations
                        r'AmazonS3',        # Java AWS SDK
                        r'AWSS3',          # Alternative naming
                        r'"s3://"',        # S3 URLs
                        r's3\.amazonaws\.com'  # S3 endpoint
                    ]
                    
                    # Check if any S3 patterns exist in the file
                    for pattern in s3_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            s3_files.append(file_path)
                            break
            except Exception:
                # Skip files that can't be read
                continue
                
        return list(set(s3_files))  # Return unique file paths

    def analyze_dependencies(self, codebase: Codebase) -> Dict[str, str]:
        """Analyze dependencies in the codebase"""
        dependencies = {}
        
        # Look for dependency files based on language
        for file_path in codebase.files:
            filename = file_path.lower()
            
            if codebase.language == codebase.language.PYTHON:
                if 'requirements.txt' in filename or 'setup.py' in filename or 'pyproject.toml' in filename:
                    try:
                        with open(file_path, 'r') as file:
                            content = file.read()
                            
                            # Extract Python dependencies
                            if 'requirements.txt' in filename:
                                for line in content.splitlines():
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        parts = line.split('==')
                                        if len(parts) >= 1:
                                            dep_name = parts[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
                                            version = parts[1].strip() if len(parts) > 1 else 'any'
                                            dependencies[dep_name] = version
                            elif 'setup.py' in filename:
                                # Simple regex to find install_requires
                                matches = re.findall(r"['\"]([^'\"]*aws[^'\"]*)['\"].*?['\"]([0-9.]+[^'\"]*)['\"]", content)
                                for match in matches:
                                    dependencies[match[0]] = match[1]
                    except Exception:
                        continue
                        
            elif codebase.language == codebase.language.JAVA:
                if 'pom.xml' in filename or 'build.gradle' in filename:
                    try:
                        with open(file_path, 'r') as file:
                            content = file.read()
                            
                            # Extract Java dependencies
                            if 'pom.xml' in filename:
                                # Find AWS dependencies in pom.xml
                                aws_matches = re.findall(r'<artifactId>([^<]*aws[^<]*)</artifactId>\s*<version>([^<]+)</version>', content)
                                for artifact_id, version in aws_matches:
                                    dependencies[artifact_id] = version
                            elif 'build.gradle' in filename:
                                # Find AWS dependencies in build.gradle
                                gradle_matches = re.findall(r'implementation.*["\']([^"\']*aws[^"\']*)["\']', content)
                                for dep in gradle_matches:
                                    # For gradle we might need version from the same line or next line
                                    dependencies[dep] = "unspecified"
                    except Exception:
                        continue
        
        return dependencies


class LLMProviderAdapter(LLMProviderPort):
    """
    Implementation of LLMProviderPort that simulates LLM interactions
    
    In a real implementation, this would connect to an actual LLM provider
    like OpenAI, Anthropic, or a local model.
    """
    
    def generate_refactoring_intent(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate refactoring intent for a specific file"""
        # In a real implementation, this would call an LLM API
        # For now, we'll return a template intent
        return f"""
        Refactor file {file_path} to replace AWS S3 API calls with Google Cloud Storage API calls.
        - Replace S3 client instantiation with GCS client
        - Update authentication from AWS credentials to GCS credentials
        - Map S3 operations (put_object, get_object, delete_object, list_objects) to GCS equivalents
        - Update error handling to match GCS client patterns
        - Preserve all surrounding code logic and control flow
        """
    
    def generate_recipe(self, analysis: Dict[str, Any]) -> str:
        """Generate OpenRewrite recipe based on analysis"""
        # In a real implementation, this would call an LLM API to generate
        # an OpenRewrite recipe based on the analysis
        # For now, we'll return a template recipe
        return f"""
        OpenRewrite Recipe for: {analysis.get('file_path', 'unknown')}
        Intent: {analysis.get('intent', 'unknown')}
        Target: {analysis.get('target', 'unknown')}
        
        This would be a real OpenRewrite recipe that transforms the code.
        """
    

class ASTTransformationAdapter(ASTTransformationPort):
    """
    Implementation of ASTTransformationPort that would integrate with OpenRewrite
    
    In a real implementation, this would interface with OpenRewrite's API
    or CLI to apply transformations to code.
    """
    
    def apply_recipe(self, recipe: str, file_path: str) -> str:
        """Apply OpenRewrite-style recipe to a file"""
        # Read the original file
        with open(file_path, 'r', encoding='utf-8') as file:
            original_content = file.read()
        
        # In a real implementation, this would call OpenRewrite to transform
        # the code based on the recipe.
        # For this simulation, we'll apply some basic transformations
        # that mimic what OpenRewrite might do for S3 to GCS migration
        
        transformed_content = original_content
        
        # Apply transformations for AWS S3 to GCS
        # This is a simplified example - real implementation would be much more sophisticated
        
        # Python transformations
        transformed_content = re.sub(
            r'import boto3',
            'from google.cloud import storage',
            transformed_content
        )
        
        transformed_content = re.sub(
            r'boto3\.client\([\'\"]s3[\'\"].*\)',
            'storage.Client()',
            transformed_content
        )
        
        # Replace common S3 operations with GCS equivalents
        transformed_content = re.sub(
            r'(\w+)\.download_file\([\'\"]([^\'\"]+)[\'\"], [\'\"]([^\'\"]+)[\'\"]\)',
            r'bucket = \1.bucket("\2")\n    blob = bucket.blob("\2")\n    blob.download_to_filename("\3")',
            transformed_content
        )
        
        transformed_content = re.sub(
            r'(\w+)\.upload_file\([\'\"]([^\'\"]+)[\'\"], [\'\"]([^\'\"]+)[\'\"]\)',
            r'bucket = \1.bucket("\3")\n    blob = bucket.blob("\3")\n    blob.upload_from_filename("\2")',
            transformed_content
        )
        
        # Add a comment indicating the file was transformed
        transformed_content = f"# TRANSFORMED BY CLOUD REFACTOR AGENT\n{transformed_content}"
        
        return transformed_content


class TestRunnerAdapter(TestRunnerPort):
    """
    Implementation of TestRunnerPort that runs tests to verify refactoring
    
    In a real implementation, this would run the actual test suite
    and return detailed results.
    """
    
    def run_tests(self, codebase: Codebase) -> Dict[str, Any]:
        """Run all tests in the codebase and return results"""
        # In a real implementation, this would run actual tests for the codebase
        # For this simulation, we'll return a mock result
        
        # This would typically run unit tests, integration tests, etc.
        # and return detailed results
        
        return {
            "success": True,
            "total_tests": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "duration": 2.5,
            "details": "All tests passed after refactoring"
        }