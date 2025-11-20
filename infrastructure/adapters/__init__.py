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
    Implementation of LLMProviderPort with Gemini support
    
    Uses Google Gemini for all LLM operations.
    Falls back to mock mode if Gemini API key is not configured.
    """
    
    def __init__(self):
        self.provider = config.LLM_PROVIDER.lower()
        self._init_provider()
    
    def _init_provider(self):
        """Initialize the Gemini LLM provider"""
        if self.provider == "gemini" and config.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=config.GEMINI_API_KEY)
                # Use gemini-2.5-flash for fast, cost-effective responses
                # Alternative: models/gemini-pro-latest or models/gemini-2.5-pro for better quality
                self.client = genai.GenerativeModel('models/gemini-2.5-flash')
                self.provider_type = "gemini"
                logger.info("Initialized Google Gemini LLM provider (using gemini-2.5-flash)")
            except ImportError:
                logger.warning("google-generativeai package not installed, falling back to mock")
                self.provider_type = "mock"
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}, falling back to mock")
                self.provider_type = "mock"
        else:
            self.provider_type = "mock"
            if not config.GEMINI_API_KEY:
                logger.info("Using mock LLM provider (set GEMINI_API_KEY to use Gemini)")
            else:
                logger.info("Using mock LLM provider (set LLM_PROVIDER=gemini to use Gemini)")
    
    def generate_refactoring_intent(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate refactoring intent using Gemini"""
        if self.provider_type == "gemini":
            return self._generate_intent_with_gemini(codebase, file_path, target)
        else:
            return self._generate_mock_intent(codebase, file_path, target)
    
    def _generate_intent_with_gemini(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate refactoring intent using Google Gemini"""
        try:
            import google.generativeai as genai
            
            # Read file content if possible
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()[:2000]  # Limit size
            except:
                file_content = "Unable to read file content"
            
            prompt = f"""Analyze the following code file and determine the refactoring intent for migrating to {target}.

File: {file_path}
Language: {codebase.language.value}

Code:
```{codebase.language.value}
{file_content}
```

Provide a concise summary of:
1. What cloud services are being used (AWS S3, Azure Blob Storage, etc.)
2. What needs to be migrated to {target}
3. Key transformation points in the code

Keep the response focused and actionable."""

            # Generate content using Gemini
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=500,
                )
            )
            
            # Proper response parsing with validation
            output = self._extract_and_validate_response(response)
            if output:
                return output
            else:
                logger.warning("Failed to extract valid response from Gemini, using mock")
                return self._generate_mock_intent(codebase, file_path, target)
                
        except Exception as e:
            logger.error(f"Gemini intent generation error: {e}, using mock")
            return self._generate_mock_intent(codebase, file_path, target)
    
    def _generate_refactoring_intent_legacy(self, codebase: Codebase, file_path: str, target: str) -> str:
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
        """Generate transformation recipe based on analysis using Gemini"""
        if self.provider_type == "gemini":
            return self._generate_recipe_with_gemini(analysis)
        else:
            return self._generate_mock_recipe(analysis)
    
    def _generate_recipe_with_gemini(self, analysis: Dict[str, Any]) -> str:
        """Generate recipe using Google Gemini"""
        try:
            import google.generativeai as genai
            
            # Build comprehensive prompt for code transformation
            code_snippet = analysis.get('code', '')[:3000]  # Limit code size
            service_type = analysis.get('service_type', 'unknown')
            language = analysis.get('language', 'python')
            target = analysis.get('target', 'gcp')
            
            prompt = f"""You are an expert code refactoring engineer specializing in cloud service migrations.

TASK: Generate a detailed transformation recipe for migrating AWS/Azure code to Google Cloud Platform (GCP).

Code to transform:
```{language}
{code_snippet}
```

Service Type: {service_type}
Target Platform: {target}
Language: {language}

CRITICAL REQUIREMENTS:
1. Generate ONLY syntactically correct Python code
2. Use proper indentation (exactly 4 spaces per level, no tabs)
3. All code must be executable and valid Python syntax
4. Include specific import statements to replace (e.g., boto3 → google.cloud.storage)
5. Provide client initialization patterns to transform
6. Map API method calls (e.g., s3.upload_file → blob.upload_from_filename)
7. Update exception handling (e.g., botocore.exceptions → google.api_core.exceptions)
8. Update configuration parameters (e.g., AWS regions → GCP regions)
9. Handle edge cases and special considerations

IMPORTANT: The output must be valid Python code that can be executed without syntax errors.
Be specific and provide exact patterns to match and their replacements."""

            # Generate recipe using Gemini with retry logic for syntax validation
            max_retries = 3
            for attempt in range(max_retries):
                response = self.client.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2 if attempt == 0 else 0.1,  # Lower temp on retry
                        max_output_tokens=2000,
                        top_p=0.95,
                    )
                )
                
                # Extract and validate response
                output = self._extract_and_validate_response(response, is_code=True)
                if output:
                    return output
                else:
                    logger.warning(f"Gemini response validation failed (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        # Enhance prompt for retry
                        prompt = self._enhance_prompt_for_retry(prompt, attempt)
            
            logger.error("All Gemini retry attempts failed, falling back to mock")
            return self._generate_mock_recipe(analysis)
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}, falling back to mock")
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
    
    def _extract_and_validate_response(self, response, is_code: bool = False) -> Optional[str]:
        """
        Extract text from Gemini response and validate syntax if it's code.
        Returns None if validation fails or response is invalid.
        """
        import ast
        
        try:
            # Check response structure
            if not response or not response.candidates:
                logger.warning("Gemini response has no candidates")
                return None
            
            candidate = response.candidates[0]
            
            # Check finish_reason
            finish_reason = getattr(candidate, 'finish_reason', None)
            if finish_reason and finish_reason != 1:  # 1 = STOP (success)
                logger.warning(f"Gemini finish_reason: {finish_reason} (1=STOP, 2=MAX_TOKENS, 3=SAFETY, etc.)")
                if finish_reason == 2:  # MAX_TOKENS - response truncated
                    logger.warning("Response truncated due to max_output_tokens limit")
                elif finish_reason == 3:  # SAFETY - content blocked
                    logger.error("Response blocked by safety filters")
                    return None
            
            # Extract text from response
            if candidate.content and candidate.content.parts:
                text = candidate.content.parts[0].text
            elif hasattr(response, 'text') and response.text:
                text = response.text
            else:
                logger.warning("No text found in Gemini response")
                return None
            
            if not text or not text.strip():
                return None
            
            # Extract code from markdown if present
            if "```python" in text:
                text = text.split("```python")[1].split("```")[0].strip()
            elif "```" in text:
                # Try to extract from generic code block
                parts = text.split("```")
                if len(parts) >= 3:
                    text = parts[1].split("\n", 1)[1] if "\n" in parts[1] else parts[1]
                    text = text.rsplit("```", 1)[0].strip()
            
            # Validate syntax if it's code
            if is_code:
                try:
                    # Try to parse as Python code
                    ast.parse(text)
                    logger.debug("Generated code passed syntax validation")
                except SyntaxError as e:
                    logger.error(f"Generated code has syntax error: {e}")
                    logger.debug(f"Invalid code snippet:\n{text[:500]}")
                    return None
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting/validating Gemini response: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _enhance_prompt_for_retry(self, original_prompt: str, attempt: int) -> str:
        """Enhance prompt with stricter requirements on retry"""
        enhancement = """
        
CRITICAL: The previous response had syntax errors. Please ensure:
1. All Python code is syntactically correct
2. Proper indentation (4 spaces per level)
3. No malformed assignments or statements
4. Complete, executable code only"""
        
        return original_prompt + enhancement
    

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