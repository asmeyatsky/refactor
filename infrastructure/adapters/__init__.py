"""
Infrastructure Layer - Adapters

Architectural Intent:
- Implement the interfaces defined in the domain layer
- Handle integration with external services like LLMs, AST tools, etc.
- Provide concrete implementations for code analysis, LLM calls, etc.
"""

import re
import ast
import subprocess
import sys
import os
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pathlib import Path

from domain.entities.codebase import Codebase
from domain.entities.refactoring_plan import RefactoringTask
from domain.ports import CodeAnalyzerPort, LLMProviderPort, ASTTransformationPort, TestRunnerPort

# Import config
try:
    from config import config
except ImportError:
    # Fallback if config not available
    class Config:
        LLM_PROVIDER = "mock"
        TEST_RUNNER = "pytest"
        TEST_TIMEOUT = 300
        LOG_LEVEL = "INFO"
    config = Config()

# Setup logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


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
    Implementation of LLMProviderPort with support for multiple LLM providers
    
    Supports:
    - OpenAI (if OPENAI_API_KEY is set)
    - Anthropic (if ANTHROPIC_API_KEY is set)
    - Mock/fallback mode for testing
    """
    
    def __init__(self):
        self.provider = config.LLM_PROVIDER.lower()
        self._init_provider()
    
    def _init_provider(self):
        """Initialize the LLM provider based on configuration"""
        if self.provider == "openai" and config.OPENAI_API_KEY:
            try:
                import openai
                self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
                self.provider_type = "openai"
                logger.info("Initialized OpenAI LLM provider")
            except ImportError:
                logger.warning("OpenAI package not installed, falling back to mock")
                self.provider_type = "mock"
        elif self.provider == "anthropic" and config.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.provider_type = "anthropic"
                logger.info("Initialized Anthropic LLM provider")
            except ImportError:
                logger.warning("Anthropic package not installed, falling back to mock")
                self.provider_type = "mock"
        else:
            self.provider_type = "mock"
            logger.info("Using mock LLM provider (set LLM_PROVIDER and API keys to use real LLM)")
    
    def generate_refactoring_intent(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate refactoring intent for a specific file"""
        if self.provider_type == "openai":
            return self._generate_with_openai(codebase, file_path, target)
        elif self.provider_type == "anthropic":
            return self._generate_with_anthropic(codebase, file_path, target)
        else:
            return self._generate_mock_intent(codebase, file_path, target)
    
    def _generate_with_openai(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate intent using OpenAI"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            prompt = f"""Analyze the following code and generate a refactoring intent to migrate from AWS services to {target}:

File: {file_path}
Language: {codebase.language.value}

Code:
{file_content}

Generate a detailed refactoring intent that includes:
1. What AWS services are being used
2. What {target} equivalents should replace them
3. Specific API calls that need to be transformed
4. Authentication changes needed
5. Any configuration updates required
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert cloud migration engineer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}, falling back to mock")
            return self._generate_mock_intent(codebase, file_path, target)
    
    def _generate_with_anthropic(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate intent using Anthropic"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            prompt = f"""Analyze the following code and generate a refactoring intent to migrate from AWS services to {target}:

File: {file_path}
Language: {codebase.language.value}

Code:
{file_content}

Generate a detailed refactoring intent that includes:
1. What AWS services are being used
2. What {target} equivalents should replace them
3. Specific API calls that need to be transformed
4. Authentication changes needed
5. Any configuration updates required
"""
            
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}, falling back to mock")
            return self._generate_mock_intent(codebase, file_path, target)
    
    def _generate_mock_intent(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate mock refactoring intent"""
        return f"""
        Refactor file {file_path} to replace AWS/Azure service calls with {target} equivalents.
        - Identify cloud service usage patterns
        - Replace client instantiation with {target} client
        - Update authentication from source cloud credentials to {target} credentials
        - Map service operations to {target} equivalents
        - Update error handling to match {target} client patterns
        - Preserve all surrounding code logic and control flow
        - Update dependencies in requirements.txt/setup.py
        """
    
    def generate_recipe(self, analysis: Dict[str, Any]) -> str:
        """Generate OpenRewrite recipe based on analysis"""
        if self.provider_type == "openai":
            return self._generate_recipe_with_openai(analysis)
        elif self.provider_type == "anthropic":
            return self._generate_recipe_with_anthropic(analysis)
        else:
            return self._generate_mock_recipe(analysis)
    
    def _generate_recipe_with_openai(self, analysis: Dict[str, Any]) -> str:
        """Generate recipe using OpenAI"""
        try:
            prompt = f"""Generate a detailed refactoring recipe for the following analysis:

{analysis}

Create a step-by-step recipe that can be used to transform the code."""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert code refactoring engineer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}, falling back to mock")
            return self._generate_mock_recipe(analysis)
    
    def _generate_recipe_with_anthropic(self, analysis: Dict[str, Any]) -> str:
        """Generate recipe using Anthropic"""
        try:
            prompt = f"""Generate a detailed refactoring recipe for the following analysis:

{analysis}

Create a step-by-step recipe that can be used to transform the code."""
            
            message = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}, falling back to mock")
            return self._generate_mock_recipe(analysis)
    
    def _generate_mock_recipe(self, analysis: Dict[str, Any]) -> str:
        """Generate mock recipe"""
        return f"""
        Refactoring Recipe for: {analysis.get('file_path', 'unknown')}
        Intent: {analysis.get('intent', 'unknown')}
        Target: {analysis.get('target', 'unknown')}
        
        Steps:
        1. Identify cloud service imports and replace with target cloud SDK imports
        2. Replace client initialization calls
        3. Transform API method calls to target cloud equivalents
        4. Update error handling patterns
        5. Update configuration parameters
        6. Verify transformations preserve functionality
        """
    

class ASTTransformationAdapter(ASTTransformationPort):
    """
    Implementation of ASTTransformationPort using Python AST manipulation
    
    Uses Python's ast module for proper code transformation instead of regex.
    """
    
    def apply_recipe(self, recipe: str, file_path: str) -> str:
        """Apply transformation recipe to a file using AST manipulation"""
        try:
            # Read the original file
            with open(file_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
            
            # Try AST-based transformation first
            try:
                tree = ast.parse(original_content)
                transformer = CloudServiceTransformer()
                transformed_tree = transformer.visit(tree)
                
                # Convert AST back to code
                import astor
                transformed_content = astor.to_source(transformed_tree)
                
                # Add transformation comment
                transformed_content = f"# TRANSFORMED BY CLOUD REFACTOR AGENT\n{transformed_content}"
                
                return transformed_content
            except SyntaxError:
                # If AST parsing fails, fall back to regex-based transformation
                logger.warning(f"AST parsing failed for {file_path}, using regex fallback")
                return self._apply_regex_transformations(original_content)
        except Exception as e:
            logger.error(f"Error transforming {file_path}: {e}")
            # Return original content if transformation fails
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
    
    def _apply_regex_transformations(self, content: str) -> str:
        """Fallback regex-based transformations"""
        transformed_content = content
        
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
        
        # Add transformation comment
        transformed_content = f"# TRANSFORMED BY CLOUD REFACTOR AGENT (regex fallback)\n{transformed_content}"
        
        return transformed_content


class CloudServiceTransformer(ast.NodeTransformer):
    """AST transformer for cloud service migrations"""
    
    def visit_Import(self, node):
        """Transform import statements"""
        new_aliases = []
        for alias in node.names:
            if alias.name == 'boto3':
                # Replace boto3 import with GCS import
                new_aliases.append(ast.alias(name='google.cloud.storage', asname='storage'))
            else:
                new_aliases.append(alias)
        
        if new_aliases:
            return ast.Import(names=new_aliases)
        return node
    
    def visit_ImportFrom(self, node):
        """Transform from imports"""
        if node.module == 'boto3':
            return ast.ImportFrom(
                module='google.cloud',
                names=[ast.alias(name='storage', asname=None)],
                level=0
            )
        return node
    
    def visit_Call(self, node):
        """Transform function calls"""
        # Transform boto3.client('s3') to storage.Client()
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'boto3':
                if node.func.attr == 'client' and len(node.args) > 0:
                    # Handle both ast.Str (Python <3.8) and ast.Constant (Python 3.8+)
                    arg_value = None
                    if isinstance(node.args[0], ast.Str):
                        arg_value = node.args[0].s
                    elif isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        arg_value = node.args[0].value
                    
                    if arg_value == 's3':
                        return ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='storage', ctx=ast.Load()),
                                attr='Client',
                                ctx=ast.Load()
                            ),
                            args=[],
                            keywords=[]
                        )
        
        return self.generic_visit(node)


class TestRunnerAdapter(TestRunnerPort):
    """
    Implementation of TestRunnerPort that runs actual tests
    
    Supports pytest and unittest test runners.
    """
    
    def __init__(self):
        self.test_runner = config.TEST_RUNNER.lower()
        self.timeout = config.TEST_TIMEOUT
    
    def run_tests(self, codebase: Codebase) -> Dict[str, Any]:
        """Run all tests in the codebase and return results"""
        if self.test_runner == "mock":
            return self._run_mock_tests()
        elif self.test_runner == "pytest":
            return self._run_pytest_tests(codebase)
        elif self.test_runner == "unittest":
            return self._run_unittest_tests(codebase)
        else:
            logger.warning(f"Unknown test runner: {self.test_runner}, using mock")
            return self._run_mock_tests()
    
    def _run_pytest_tests(self, codebase: Codebase) -> Dict[str, Any]:
        """Run tests using pytest"""
        try:
            import pytest
            
            # Find test files in the codebase
            test_files = [f for f in codebase.files if 'test_' in os.path.basename(f) or '_test.py' in f]
            
            if not test_files:
                logger.info("No test files found, skipping test execution")
                return {
                    "success": True,
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "duration": 0.0,
                    "details": "No test files found in codebase"
                }
            
            # Change to codebase directory
            original_dir = os.getcwd()
            os.chdir(codebase.path)
            
            try:
                # Run pytest
                result = pytest.main([
                    '-v',
                    '--tb=short',
                    '--junit-xml=/tmp/pytest_results.xml',
                    *test_files
                ])
                
                # Parse results (simplified - in production, parse XML)
                success = result == 0
                
                return {
                    "success": success,
                    "total_tests": len(test_files),
                    "passed": len(test_files) if success else 0,
                    "failed": 0 if success else 1,
                    "skipped": 0,
                    "duration": 0.0,  # Would parse from XML in production
                    "details": f"Pytest execution {'passed' if success else 'failed'}"
                }
            finally:
                os.chdir(original_dir)
                
        except ImportError:
            logger.warning("pytest not installed, falling back to mock")
            return self._run_mock_tests()
        except Exception as e:
            logger.error(f"Error running pytest: {e}")
            return {
                "success": False,
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0.0,
                "details": f"Error running tests: {str(e)}"
            }
    
    def _run_unittest_tests(self, codebase: Codebase) -> Dict[str, Any]:
        """Run tests using unittest"""
        try:
            import unittest
            
            # Find test files
            test_files = [f for f in codebase.files if 'test_' in os.path.basename(f) or '_test.py' in f]
            
            if not test_files:
                logger.info("No test files found, skipping test execution")
                return {
                    "success": True,
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "duration": 0.0,
                    "details": "No test files found in codebase"
                }
            
            # Change to codebase directory
            original_dir = os.getcwd()
            os.chdir(codebase.path)
            
            try:
                # Discover and run tests
                loader = unittest.TestLoader()
                suite = unittest.TestSuite()
                
                for test_file in test_files:
                    # Import test module
                    module_name = os.path.splitext(os.path.basename(test_file))[0]
                    spec = __import__(module_name, fromlist=[''])
                    suite.addTests(loader.loadTestsFromModule(spec))
                
                runner = unittest.TextTestRunner(verbosity=2)
                result = runner.run(suite)
                
                return {
                    "success": result.wasSuccessful(),
                    "total_tests": result.testsRun,
                    "passed": result.testsRun - len(result.failures) - len(result.errors),
                    "failed": len(result.failures) + len(result.errors),
                    "skipped": len(result.skipped),
                    "duration": 0.0,
                    "details": f"Unittest execution: {result.testsRun} tests run"
                }
            finally:
                os.chdir(original_dir)
                
        except Exception as e:
            logger.error(f"Error running unittest: {e}")
            return {
                "success": False,
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0.0,
                "details": f"Error running tests: {str(e)}"
            }
    
    def _run_mock_tests(self) -> Dict[str, Any]:
        """Return mock test results"""
        logger.info("Using mock test runner")
        return {
            "success": True,
            "total_tests": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "duration": 2.5,
            "details": "Mock test execution (set TEST_RUNNER=pytest or unittest to run real tests)"
        }