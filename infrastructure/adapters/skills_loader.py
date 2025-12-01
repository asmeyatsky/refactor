"""
Skills Loader Module

Architectural Intent:
- Load and parse SKILL.md to extract architectural principles
- Provide skills context to LLM providers for code generation
- Enforce architectural standards during code transformation
- Follow Clean Architecture: This is an infrastructure adapter that reads external configuration

Key Design Decisions:
1. Skills are loaded once and cached for performance
2. Skills are formatted as prompts for LLM consumption
3. Skills validation can be performed on generated code
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SkillsLoader:
    """
    Loads and manages architectural skills from SKILL.md
    
    This adapter reads the SKILL.md file and provides formatted
    skills context for LLM code generation.
    """
    
    def __init__(self, skills_file_path: Optional[str] = None):
        """
        Initialize the skills loader
        
        Args:
            skills_file_path: Optional path to SKILL.md file.
                            Defaults to SKILL.md in project root.
        """
        if skills_file_path is None:
            # Default to SKILL.md in project root
            project_root = Path(__file__).parent.parent.parent
            skills_file_path = project_root / "SKILL.md"
        
        self.skills_file_path = Path(skills_file_path)
        self._skills_content: Optional[str] = None
        self._skills_prompt: Optional[str] = None
    
    def load_skills(self) -> str:
        """
        Load skills content from SKILL.md
        
        Returns:
            Content of SKILL.md as string
            
        Raises:
            FileNotFoundError: If SKILL.md doesn't exist
            IOError: If file cannot be read
        """
        if self._skills_content is None:
            if not self.skills_file_path.exists():
                raise FileNotFoundError(
                    f"SKILL.md not found at {self.skills_file_path}. "
                    "Please ensure SKILL.md exists in the project root."
                )
            
            try:
                with open(self.skills_file_path, 'r', encoding='utf-8') as f:
                    self._skills_content = f.read()
                logger.info(f"Loaded skills from {self.skills_file_path}")
            except Exception as e:
                raise IOError(f"Failed to read SKILL.md: {e}")
        
        return self._skills_content
    
    def get_skills_prompt(self) -> str:
        """
        Get formatted skills as a prompt for LLM code generation
        
        Returns:
            Formatted prompt string that can be prepended to LLM requests
        """
        if self._skills_prompt is None:
            skills_content = self.load_skills()
            
            # Format as a prompt for LLM
            self._skills_prompt = f"""You are a code generation assistant that MUST follow these architectural principles:

{skills_content}

When generating code, you MUST:
1. Follow all four core architectural principles (SoC, DDD, Clean/Hexagonal Architecture, High Cohesion/Low Coupling)
2. Adhere to all five non-negotiable rules
3. Verify the implementation checklist before returning code
4. Include architectural intent documentation in code comments
5. Ensure domain models are immutable where possible
6. Use ports and adapters pattern for external dependencies
7. Keep business logic out of infrastructure components

Generate code that strictly adheres to these principles."""
        
        return self._skills_prompt
    
    def get_skills_summary(self) -> Dict[str, any]:
        """
        Extract key architectural principles as structured data
        
        Returns:
            Dictionary with architectural principles and rules
        """
        skills_content = self.load_skills()
        
        return {
            "core_principles": [
                "Separation of Concerns (SoC)",
                "Domain-Driven Design (DDD)",
                "Clean/Hexagonal Architecture",
                "High Cohesion, Low Coupling"
            ],
            "non_negotiable_rules": [
                "Zero Business Logic in Infrastructure Components",
                "Interface-First Development (Ports and Adapters)",
                "Immutable Domain Models",
                "Mandatory Testing Coverage",
                "Documentation of Architectural Intent"
            ],
            "full_content": skills_content
        }
    
    def validate_code_structure(self, code: str, language: str = "python") -> Dict[str, any]:
        """
        Validate that generated code follows architectural principles
        
        This is a basic validation - full validation would require AST parsing
        
        Args:
            code: Generated code to validate
            language: Programming language of the code
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "has_architectural_intent": False,
            "has_immutable_models": False,
            "has_interface_definitions": False,
            "has_tests": False,
            "violations": []
        }
        
        code_lower = code.lower()
        
        # Check for architectural intent documentation
        if any(keyword in code_lower for keyword in [
            "architectural intent", "design decision", "domain model",
            "aggregate", "entity", "value object"
        ]):
            validation_results["has_architectural_intent"] = True
        
        # Check for immutable models (frozen dataclasses, etc.)
        if language == "python":
            if "@dataclass(frozen=true)" in code_lower or "frozen=true" in code_lower:
                validation_results["has_immutable_models"] = True
        elif language == "java":
            if "final" in code_lower and "class" in code_lower:
                validation_results["has_immutable_models"] = True
        
        # Check for interface definitions
        if language == "python":
            if "abc" in code_lower or "abstractmethod" in code_lower or "protocol" in code_lower:
                validation_results["has_interface_definitions"] = True
        elif language == "java":
            if "interface" in code_lower:
                validation_results["has_interface_definitions"] = True
        
        # Check for tests (basic check)
        if "test" in code_lower or "assert" in code_lower:
            validation_results["has_tests"] = True
        
        # Check for violations
        # Business logic in infrastructure (heuristic: checking for business keywords in adapter/repository files)
        if any(keyword in code_lower for keyword in ["adapter", "repository", "infrastructure"]):
            business_keywords = ["calculate", "validate", "process", "transform", "business"]
            if any(keyword in code_lower for keyword in business_keywords):
                # This is a heuristic - might be false positive
                validation_results["violations"].append(
                    "Potential business logic in infrastructure layer"
                )
        
        return validation_results
    
    def reload(self):
        """Reload skills from file (useful if SKILL.md is updated)"""
        self._skills_content = None
        self._skills_prompt = None
        logger.info("Skills cache cleared, will reload on next access")


# Singleton instance for easy access
_skills_loader_instance: Optional[SkillsLoader] = None


def get_skills_loader() -> SkillsLoader:
    """
    Get singleton instance of SkillsLoader
    
    Returns:
        SkillsLoader instance
    """
    global _skills_loader_instance
    if _skills_loader_instance is None:
        _skills_loader_instance = SkillsLoader()
    return _skills_loader_instance
