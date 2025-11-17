"""
Domain Ports (Interfaces)

Architectural Intent:
- Define the interfaces for external dependencies
- Enable dependency inversion following the Dependency Inversion Principle
- Allow for easy testing and multiple implementations of external services
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan, RefactoringTask


class CodeAnalyzerPort(ABC):
    """Interface for code analysis services"""
    
    @abstractmethod
    def identify_aws_s3_usage(self, codebase: Codebase) -> List[str]:
        """Identify all files containing AWS S3 usage"""
        pass
    
    @abstractmethod
    def analyze_dependencies(self, codebase: Codebase) -> Dict[str, str]:
        """Analyze dependencies in the codebase"""
        pass


class LLMProviderPort(ABC):
    """Interface for LLM providers"""
    
    @abstractmethod
    def generate_refactoring_intent(self, codebase: Codebase, file_path: str, target: str) -> str:
        """Generate refactoring intent for a specific file"""
        pass
    
    @abstractmethod
    def generate_recipe(self, analysis: Dict[str, Any]) -> str:
        """Generate OpenRewrite recipe based on analysis"""
        pass


class ASTTransformationPort(ABC):
    """Interface for AST transformation services"""
    
    @abstractmethod
    def apply_recipe(self, recipe: str, file_path: str) -> str:
        """Apply OpenRewrite-style recipe to a file"""
        pass


class TestRunnerPort(ABC):
    """Interface for test execution services"""
    
    @abstractmethod
    def run_tests(self, codebase: Codebase) -> Dict[str, Any]:
        """Run all tests in the codebase and return results"""
        pass


class FileRepositoryPort(ABC):
    """Interface for file operations"""
    
    @abstractmethod
    def read_file(self, file_path: str) -> str:
        """Read content from a file"""
        pass
    
    @abstractmethod
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file"""
        pass
    
    @abstractmethod
    def create_backup(self, file_path: str) -> str:
        """Create a backup of a file and return backup path"""
        pass


class CodebaseRepositoryPort(ABC):
    """Interface for codebase persistence"""
    
    @abstractmethod
    def save(self, codebase: Codebase) -> None:
        """Save a codebase"""
        pass
    
    @abstractmethod
    def load(self, codebase_id: str) -> Optional[Codebase]:
        """Load a codebase by ID"""
        pass


class PlanRepositoryPort(ABC):
    """Interface for refactoring plan persistence"""
    
    @abstractmethod
    def save(self, plan: RefactoringPlan) -> None:
        """Save a refactoring plan"""
        pass
    
    @abstractmethod
    def load(self, plan_id: str) -> Optional[RefactoringPlan]:
        """Load a refactoring plan by ID"""
        pass