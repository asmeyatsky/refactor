"""
Test Execution Framework

Architectural Intent:
- Executes tests after migration to verify correctness
- Supports multiple test frameworks (pytest, unittest, jest, junit)
- Provides test results and coverage reporting
"""

import os
import subprocess
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TestFramework(Enum):
    """Supported test frameworks"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    JUNIT = "junit"
    MOCHA = "mocha"
    UNKNOWN = "unknown"


class TestStatus(Enum):
    """Test execution status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    status: TestStatus
    duration: float  # seconds
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Result of a test suite execution"""
    framework: TestFramework
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float  # seconds
    test_results: List[TestResult]
    coverage: Optional[float] = None  # Coverage percentage if available
    output: Optional[str] = None
    success: bool = False


class TestExecutionFramework:
    """
    Executes tests and collects results across multiple frameworks
    """
    
    def __init__(self, repository_path: str):
        self.repository_path = repository_path
        self.detected_framework: Optional[TestFramework] = None
    
    def detect_test_framework(self) -> TestFramework:
        """Detect the test framework used in the repository"""
        # Check for pytest
        if os.path.exists(os.path.join(self.repository_path, 'pytest.ini')) or \
           os.path.exists(os.path.join(self.repository_path, 'pyproject.toml')):
            # Check pyproject.toml for pytest config
            try:
                pyproject_path = os.path.join(self.repository_path, 'pyproject.toml')
                if os.path.exists(pyproject_path):
                    with open(pyproject_path, 'r') as f:
                        content = f.read()
                        if 'pytest' in content.lower() or '[tool.pytest' in content:
                            self.detected_framework = TestFramework.PYTEST
                            return TestFramework.PYTEST
            except Exception:
                pass
        
        # Check for test files
        test_files = self._find_test_files()
        
        # Python test files
        python_tests = [f for f in test_files if f.endswith('.py')]
        if python_tests:
            # Check if pytest-style (test_*.py or *_test.py)
            pytest_style = any(
                os.path.basename(f).startswith('test_') or 
                os.path.basename(f).endswith('_test.py')
                for f in python_tests
            )
            if pytest_style:
                # Check for pytest imports
                for test_file in python_tests[:5]:  # Check first 5
                    try:
                        with open(test_file, 'r') as f:
                            content = f.read()
                            if 'import pytest' in content or 'from pytest import' in content:
                                self.detected_framework = TestFramework.PYTEST
                                return TestFramework.PYTEST
                            elif 'import unittest' in content or 'from unittest import' in content:
                                self.detected_framework = TestFramework.UNITTEST
                                return TestFramework.UNITTEST
                    except Exception:
                        continue
                # Default to pytest if pytest-style naming
                self.detected_framework = TestFramework.PYTEST
                return TestFramework.PYTEST
            else:
                self.detected_framework = TestFramework.UNITTEST
                return TestFramework.UNITTEST
        
        # JavaScript/TypeScript test files
        js_tests = [f for f in test_files if f.endswith(('.test.js', '.test.ts', '.spec.js', '.spec.ts'))]
        if js_tests:
            # Check package.json for test framework
            package_json_path = os.path.join(self.repository_path, 'package.json')
            if os.path.exists(package_json_path):
                try:
                    with open(package_json_path, 'r') as f:
                        package_json = json.load(f)
                        scripts = package_json.get('scripts', {})
                        deps = package_json.get('dependencies', {})
                        dev_deps = package_json.get('devDependencies', {})
                        
                        if 'jest' in deps or 'jest' in dev_deps or 'jest' in str(scripts):
                            self.detected_framework = TestFramework.JEST
                            return TestFramework.JEST
                        elif 'mocha' in deps or 'mocha' in dev_deps or 'mocha' in str(scripts):
                            self.detected_framework = TestFramework.MOCHA
                            return TestFramework.MOCHA
                except Exception:
                    pass
        
        # Java test files
        java_tests = [f for f in test_files if f.endswith('Test.java')]
        if java_tests:
            self.detected_framework = TestFramework.JUNIT
            return TestFramework.JUNIT
        
        return TestFramework.UNKNOWN
    
    def _find_test_files(self) -> List[str]:
        """Find all test files in repository"""
        test_files = []
        
        for root, dirs, files in os.walk(self.repository_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target', '.idea']]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.repository_path)
                
                # Python tests
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(relative_path)
                elif file.endswith('_test.py'):
                    test_files.append(relative_path)
                
                # JavaScript/TypeScript tests
                if file.endswith(('.test.js', '.test.ts', '.spec.js', '.spec.ts')):
                    test_files.append(relative_path)
                
                # Java tests
                if file.endswith('Test.java'):
                    test_files.append(relative_path)
        
        return test_files
    
    def execute_tests(self, framework: Optional[TestFramework] = None) -> TestSuiteResult:
        """
        Execute tests using detected or specified framework
        
        Args:
            framework: Optional framework to use (auto-detects if not provided)
            
        Returns:
            TestSuiteResult with execution results
        """
        if framework is None:
            framework = self.detect_test_framework()
        
        if framework == TestFramework.PYTEST:
            return self._execute_pytest()
        elif framework == TestFramework.UNITTEST:
            return self._execute_unittest()
        elif framework == TestFramework.JEST:
            return self._execute_jest()
        elif framework == TestFramework.JUNIT:
            return self._execute_junit()
        elif framework == TestFramework.MOCHA:
            return self._execute_mocha()
        else:
            return TestSuiteResult(
                framework=framework,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                test_results=[],
                success=False,
                output="Test framework not supported or not detected"
            )
    
    def _execute_pytest(self) -> TestSuiteResult:
        """Execute pytest tests"""
        try:
            # Run pytest with JSON output
            cmd = ['pytest', '--tb=short', '--json-report', '--json-report-file=/tmp/pytest_report.json', '-v']
            
            result = subprocess.run(
                cmd,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse JSON report if available
            test_results = []
            total_tests = 0
            passed = 0
            failed = 0
            skipped = 0
            errors = 0
            
            json_report_path = '/tmp/pytest_report.json'
            if os.path.exists(json_report_path):
                try:
                    with open(json_report_path, 'r') as f:
                        report = json.load(f)
                    
                    total_tests = report.get('summary', {}).get('total', 0)
                    passed = report.get('summary', {}).get('passed', 0)
                    failed = report.get('summary', {}).get('failed', 0)
                    skipped = report.get('summary', {}).get('skipped', 0)
                    errors = report.get('summary', {}).get('error', 0)
                    
                    # Parse individual test results
                    for test in report.get('tests', []):
                        test_results.append(TestResult(
                            test_name=test.get('nodeid', 'unknown'),
                            status=TestStatus.PASSED if test.get('outcome') == 'passed' else
                                   TestStatus.FAILED if test.get('outcome') == 'failed' else
                                   TestStatus.SKIPPED if test.get('outcome') == 'skipped' else
                                   TestStatus.ERROR,
                            duration=test.get('duration', 0.0),
                            error_message=test.get('call', {}).get('longrepr') if test.get('outcome') != 'passed' else None
                        ))
                except Exception:
                    pass
            
            # Fallback: parse stdout if JSON report not available
            if total_tests == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line.lower() and 'failed' in line.lower():
                        # Extract numbers from line like "5 passed, 2 failed"
                        import re
                        matches = re.findall(r'(\d+)\s+(passed|failed|skipped)', line.lower())
                        for count, status in matches:
                            count = int(count)
                            total_tests += count
                            if status == 'passed':
                                passed += count
                            elif status == 'failed':
                                failed += count
                            elif status == 'skipped':
                                skipped += count
            
            return TestSuiteResult(
                framework=TestFramework.PYTEST,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration=0.0,  # Would need to track separately
                test_results=test_results,
                success=result.returncode == 0 and failed == 0,
                output=result.stdout + result.stderr
            )
            
        except subprocess.TimeoutExpired:
            return TestSuiteResult(
                framework=TestFramework.PYTEST,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=300.0,
                test_results=[],
                success=False,
                output="Test execution timed out after 5 minutes"
            )
        except Exception as e:
            return TestSuiteResult(
                framework=TestFramework.PYTEST,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[],
                success=False,
                output=f"Error executing pytest: {str(e)}"
            )
    
    def _execute_unittest(self) -> TestSuiteResult:
        """Execute unittest tests"""
        try:
            # Find test files
            test_files = self._find_test_files()
            python_tests = [f for f in test_files if f.endswith('.py')]
            
            if not python_tests:
                return TestSuiteResult(
                    framework=TestFramework.UNITTEST,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=0,
                    duration=0.0,
                    test_results=[],
                    success=True,
                    output="No test files found"
                )
            
            # Run unittest discover
            cmd = ['python', '-m', 'unittest', 'discover', '-s', '.', '-p', 'test_*.py', '-v']
            
            result = subprocess.run(
                cmd,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse output
            lines = result.stdout.split('\n')
            total_tests = 0
            passed = 0
            failed = 0
            
            for line in lines:
                if 'Ran' in line and 'test' in line.lower():
                    import re
                    match = re.search(r'Ran\s+(\d+)\s+test', line)
                    if match:
                        total_tests = int(match.group(1))
                if 'OK' in line:
                    passed = total_tests
                if 'FAILED' in line or 'ERROR' in line:
                    failed = total_tests - passed
            
            return TestSuiteResult(
                framework=TestFramework.UNITTEST,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=0,
                errors=0,
                duration=0.0,
                test_results=[],
                success=result.returncode == 0,
                output=result.stdout + result.stderr
            )
            
        except Exception as e:
            return TestSuiteResult(
                framework=TestFramework.UNITTEST,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[],
                success=False,
                output=f"Error executing unittest: {str(e)}"
            )
    
    def _execute_jest(self) -> TestSuiteResult:
        """Execute Jest tests"""
        try:
            # Check if node_modules exists, install if needed
            if not os.path.exists(os.path.join(self.repository_path, 'node_modules')):
                # Try to install dependencies
                subprocess.run(
                    ['npm', 'install'],
                    cwd=self.repository_path,
                    capture_output=True,
                    timeout=300
                )
            
            # Run jest with JSON output
            cmd = ['npm', 'test', '--', '--json', '--outputFile=/tmp/jest_report.json']
            
            result = subprocess.run(
                cmd,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse JSON report
            test_results = []
            total_tests = 0
            passed = 0
            failed = 0
            
            json_report_path = '/tmp/jest_report.json'
            if os.path.exists(json_report_path):
                try:
                    with open(json_report_path, 'r') as f:
                        report = json.load(f)
                    
                    total_tests = report.get('numTotalTests', 0)
                    passed = report.get('numPassedTests', 0)
                    failed = report.get('numFailedTests', 0)
                    
                    # Parse test results
                    for test_result in report.get('testResults', []):
                        for assertion in test_result.get('assertionResults', []):
                            test_results.append(TestResult(
                                test_name=assertion.get('fullName', 'unknown'),
                                status=TestStatus.PASSED if assertion.get('status') == 'passed' else TestStatus.FAILED,
                                duration=assertion.get('duration', 0.0) / 1000.0,  # Convert ms to seconds
                                error_message=assertion.get('failureMessages', [None])[0] if assertion.get('status') != 'passed' else None
                            ))
                except Exception:
                    pass
            
            return TestSuiteResult(
                framework=TestFramework.JEST,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=0,
                errors=0,
                duration=0.0,
                test_results=test_results,
                success=result.returncode == 0 and failed == 0,
                output=result.stdout + result.stderr
            )
            
        except Exception as e:
            return TestSuiteResult(
                framework=TestFramework.JEST,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[],
                success=False,
                output=f"Error executing Jest: {str(e)}"
            )
    
    def _execute_junit(self) -> TestSuiteResult:
        """Execute JUnit tests"""
        try:
            # Try Maven first
            if os.path.exists(os.path.join(self.repository_path, 'pom.xml')):
                cmd = ['mvn', 'test']
            # Try Gradle
            elif os.path.exists(os.path.join(self.repository_path, 'build.gradle')):
                cmd = ['./gradlew', 'test']
            else:
                return TestSuiteResult(
                    framework=TestFramework.JUNIT,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=1,
                    duration=0.0,
                    test_results=[],
                    success=False,
                    output="No Maven or Gradle build file found"
                )
            
            result = subprocess.run(
                cmd,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for Java builds
            )
            
            # Parse test results (simplified)
            total_tests = 0
            passed = 0
            failed = 0
            
            # Look for test reports
            test_report_dirs = [
                os.path.join(self.repository_path, 'target', 'surefire-reports'),
                os.path.join(self.repository_path, 'build', 'test-results'),
            ]
            
            for report_dir in test_report_dirs:
                if os.path.exists(report_dir):
                    # Parse XML reports
                    for xml_file in Path(report_dir).glob('*.xml'):
                        try:
                            tree = ET.parse(xml_file)
                            root = tree.getroot()
                            total_tests += int(root.get('tests', 0))
                            passed += int(root.get('successful', 0))
                            failed += int(root.get('failures', 0)) + int(root.get('errors', 0))
                        except Exception:
                            continue
            
            return TestSuiteResult(
                framework=TestFramework.JUNIT,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=0,
                errors=0,
                duration=0.0,
                test_results=[],
                success=result.returncode == 0 and failed == 0,
                output=result.stdout + result.stderr
            )
            
        except Exception as e:
            return TestSuiteResult(
                framework=TestFramework.JUNIT,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[],
                success=False,
                output=f"Error executing JUnit tests: {str(e)}"
            )
    
    def _execute_mocha(self) -> TestSuiteResult:
        """Execute Mocha tests"""
        try:
            # Check if node_modules exists
            if not os.path.exists(os.path.join(self.repository_path, 'node_modules')):
                subprocess.run(['npm', 'install'], cwd=self.repository_path, capture_output=True, timeout=300)
            
            # Run mocha with JSON reporter
            cmd = ['npx', 'mocha', '--reporter', 'json', '--timeout', '30000']
            
            result = subprocess.run(
                cmd,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse JSON output
            test_results = []
            total_tests = 0
            passed = 0
            failed = 0
            
            try:
                report = json.loads(result.stdout)
                total_tests = report.get('tests', 0)
                passed = report.get('passes', 0)
                failed = report.get('failures', 0)
                
                for test in report.get('tests', []):
                    test_results.append(TestResult(
                        test_name=test.get('fullTitle', 'unknown'),
                        status=TestStatus.PASSED if test.get('state') == 'passed' else TestStatus.FAILED,
                        duration=test.get('duration', 0.0),
                        error_message=test.get('err', {}).get('message') if test.get('state') != 'passed' else None
                    ))
            except Exception:
                pass
            
            return TestSuiteResult(
                framework=TestFramework.MOCHA,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=0,
                errors=0,
                duration=0.0,
                test_results=test_results,
                success=result.returncode == 0 and failed == 0,
                output=result.stdout + result.stderr
            )
            
        except Exception as e:
            return TestSuiteResult(
                framework=TestFramework.MOCHA,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                test_results=[],
                success=False,
                output=f"Error executing Mocha: {str(e)}"
            )
