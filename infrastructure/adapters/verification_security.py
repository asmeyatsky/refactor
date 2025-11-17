"""
Verification and Security Gate Modules

Architectural Intent:
- Implement the Verification Agent as described in the PRD
- Provide mandatory verification of refactored code
- Ensure behavior preservation and security compliance
- Implement the "De-Hallucinator Pattern" to mitigate LLM output issues
"""

import re
from typing import Dict, Any, List
from datetime import datetime

from domain.entities.codebase import Codebase
from domain.entities.refactoring_plan import RefactoringPlan
from domain.ports import TestRunnerPort
from domain.value_objects import RefactoringResult


class VerificationAgent:
    """
    Verification Agent (The Gatekeeper)
    
    As described in the PRD, this serves as a mandatory gate to mitigate
    inconsistency and generation of erroneous output (hallucination smell).
    """
    
    def __init__(self, test_runner: TestRunnerPort):
        self.test_runner = test_runner

    def verify_refactoring_result(
        self, 
        original_codebase: Codebase, 
        refactored_codebase: Codebase, 
        plan: RefactoringPlan
    ) -> RefactoringResult:
        """
        Verify that the refactoring preserved behavior and meets quality standards
        """
        # Run tests to verify behavior preservation
        test_results = self.test_runner.run_tests(refactored_codebase)
        test_success = test_results.get("success", False)
        
        errors = []
        warnings = []
        
        # Check if all tests passed (NFR-Q1: Behavior Preservation)
        if not test_success:
            errors.append("Tests failed after refactoring - behavior not preserved")
        
        # Verify that the plan was executed completely
        failed_tasks = plan.get_failed_tasks()
        if failed_tasks:
            errors.append(f"Refactoring plan had {len(failed_tasks)} failed tasks")
        
        # Check for potential security issues
        security_issues = self._check_security_issues(refactored_codebase)
        if security_issues:
            errors.extend(security_issues)
        
        # Check for code quality issues
        quality_warnings = self._check_quality_issues(refactored_codebase)
        if quality_warnings:
            warnings.extend(quality_warnings)
        
        success = len(errors) == 0 and test_success
        
        return RefactoringResult(
            success=success,
            message="Verification completed" if success else f"Verification failed with {len(errors)} errors",
            transformed_files=len([task for task in plan.tasks if task.status.name == 'COMPLETED']),
            errors=errors,
            warnings=warnings
        )
    
    def _check_security_issues(self, codebase: Codebase) -> List[str]:
        """Check for potential security issues in the refactored code"""
        security_issues = []
        
        for file_path in codebase.files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    
                    # Check for hardcoded credentials
                    if re.search(r'(?i)(secret|key|password|token).*=["\'][a-zA-Z0-9+/=]{20,}["\']', content):
                        security_issues.append(f"Potential hardcoded credential found in {file_path}")
                    
                    # Check for insecure configurations
                    if 'verify=False' in content or 'insecure' in content.lower():
                        security_issues.append(f"Potential security misconfiguration in {file_path}")
            except Exception:
                continue
                
        return security_issues
    
    def _check_quality_issues(self, codebase: Codebase) -> List[str]:
        """Check for code quality issues"""
        quality_warnings = []
        
        for file_path in codebase.files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    
                    # Check for TODO/FIXME comments that might indicate incomplete refactoring
                    if 'TODO' in content or 'FIXME' in content:
                        quality_warnings.append(f"TODO/FIXME comments found in {file_path}")
                    
                    # Check for potential performance issues
                    if re.search(r'for.*in.*range\([0-9]{6,}\)', content):  # Large loops
                        quality_warnings.append(f"Potential performance issue: large loop in {file_path}")
            except Exception:
                continue
                
        return quality_warnings


class SecurityGate:
    """
    Security Gate Implementation
    
    Implements NFR-S1, NFR-S2, and NFR-S3 from the PRD
    """
    
    def __init__(self, verification_agent: VerificationAgent):
        self.verification_agent = verification_agent

    def validate_code_changes(self, original_codebase: Codebase, refactored_codebase: Codebase, plan: RefactoringPlan) -> bool:
        """
        Validate that the code changes meet security requirements
        """
        # Verify that the refactoring preserves behavior
        verification_result = self.verification_agent.verify_refactoring_result(
            original_codebase, 
            refactored_codebase, 
            plan
        )
        
        return verification_result.success
    
    def validate_input(self, input_data: str) -> bool:
        """
        Validate user input to prevent prompt injection attacks
        """
        # Check for potential prompt injection patterns
        injection_patterns = [
            r'<\|.*\|>',      # Potential template injection
            r'##\s+.*',       # Attempt to change context
            r'```\s*sql',     # Attempt to execute SQL
            r'exec\(|system\(|os\.|subprocess\('  # System command execution
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                return False
                
        return True


import re


def sanitize_input(user_input: str) -> str:
    """
    Sanitize user input to prevent injection attacks
    Implements NFR-S2: Input Validation and Sanitization
    """
    # Remove potentially dangerous patterns
    sanitized = re.sub(r'<\|.*?\|>', '', user_input)  # Remove template delimiters
    sanitized = re.sub(r'```\s*sql.*?```', '', sanitized, flags=re.DOTALL)  # Remove SQL blocks
    
    return sanitized.strip()


def validate_code_semantics(code_content: str, language: str) -> List[str]:
    """
    Validate code semantics to catch potential hallucinations
    """
    issues = []
    
    # Check for syntactic consistency
    if language.lower() == 'python':
        # Check for obvious Python syntax issues
        if code_content.count('(') != code_content.count(')'):
            issues.append("Unbalanced parentheses detected")
        if code_content.count('[') != code_content.count(']'):
            issues.append("Unbalanced brackets detected")
        if code_content.count('{') != code_content.count('}'):
            issues.append("Unbalanced braces detected")
    
    return issues