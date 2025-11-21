"""
Migration Assessment Report (MAR) Value Object

Architectural Intent:
- Represents a pre-migration analysis report
- Contains service detection, change estimates, and risk assessment
- Immutable value object for data transfer
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    """Risk level for migration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ServiceComplexity(Enum):
    """Complexity level for service migration"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass(frozen=True)
class DetectedService:
    """Represents a detected cloud service in the repository"""
    service_name: str
    service_type: str  # 'aws' or 'azure'
    files_affected: List[str]
    estimated_changes: int  # Estimated lines of code to change
    complexity: ServiceComplexity
    confidence: float  # 0.0 to 1.0
    patterns_found: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CrossFileDependency:
    """Represents a cross-file dependency"""
    source_file: str
    target_file: str
    dependency_type: str  # 'import', 'constant', 'variable', 'function'
    dependency_name: str
    usage_count: int = 1


@dataclass(frozen=True)
class InfrastructureFile:
    """Represents an Infrastructure as Code file"""
    file_path: str
    file_type: str  # 'terraform', 'cloudformation', 'pulumi', 'yaml', 'json'
    services_referenced: List[str]
    estimated_changes: int


@dataclass(frozen=True)
class MigrationAssessmentReport:
    """
    Migration Assessment Report (MAR)
    
    Immutable value object containing pre-migration analysis results.
    """
    repository_id: str
    repository_url: str
    branch: str
    generated_at: datetime
    
    # Repository Summary
    total_files: int
    total_lines: int
    languages_detected: List[str]
    
    # Cloud Services Detected
    services_detected: List[DetectedService]
    
    # Change Estimates
    total_estimated_changes: int
    files_to_modify: List[str]
    files_to_modify_count: int
    
    # Cross-File Dependencies
    cross_file_dependencies: List[CrossFileDependency]
    
    # Infrastructure Files
    infrastructure_files: List[InfrastructureFile]
    
    # Risk Assessment
    confidence_score: float  # 0.0 to 1.0
    overall_risk: RiskLevel
    risks: List[str] = field(default_factory=list)
    
    # Test Strategy
    existing_tests_found: bool = False
    test_files: List[str] = field(default_factory=list)
    test_framework: Optional[str] = None
    
    # Migration Plan
    recommended_services: List[str] = field(default_factory=list)
    estimated_duration_minutes: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert MAR to dictionary for serialization"""
        return {
            "repository_id": self.repository_id,
            "repository_url": self.repository_url,
            "branch": self.branch,
            "generated_at": self.generated_at.isoformat(),
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "languages_detected": self.languages_detected,
            "services_detected": [
                {
                    "service_name": s.service_name,
                    "service_type": s.service_type,
                    "files_affected": s.files_affected,
                    "estimated_changes": s.estimated_changes,
                    "complexity": s.complexity.value,
                    "confidence": s.confidence,
                    "patterns_found": s.patterns_found
                }
                for s in self.services_detected
            ],
            "total_estimated_changes": self.total_estimated_changes,
            "files_to_modify": self.files_to_modify,
            "files_to_modify_count": self.files_to_modify_count,
            "cross_file_dependencies": [
                {
                    "source_file": d.source_file,
                    "target_file": d.target_file,
                    "dependency_type": d.dependency_type,
                    "dependency_name": d.dependency_name,
                    "usage_count": d.usage_count
                }
                for d in self.cross_file_dependencies
            ],
            "infrastructure_files": [
                {
                    "file_path": f.file_path,
                    "file_type": f.file_type,
                    "services_referenced": f.services_referenced,
                    "estimated_changes": f.estimated_changes
                }
                for f in self.infrastructure_files
            ],
            "confidence_score": self.confidence_score,
            "overall_risk": self.overall_risk.value,
            "risks": self.risks,
            "existing_tests_found": self.existing_tests_found,
            "test_files": self.test_files,
            "test_framework": self.test_framework,
            "recommended_services": self.recommended_services,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "metadata": self.metadata
        }
    
    def to_markdown(self) -> str:
        """Convert MAR to Markdown format for PR descriptions"""
        md = f"""# Migration Assessment Report (MAR)

## Repository Information
- **Repository**: {self.repository_url}
- **Branch**: {self.branch}
- **Generated**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Repository Summary
- **Total Files**: {self.total_files}
- **Total Lines of Code**: {self.total_lines:,}
- **Languages Detected**: {', '.join(self.languages_detected) if self.languages_detected else 'None detected'}

## Cloud Services Detected

"""
        for service in self.services_detected:
            md += f"""### {service.service_name} ({service.service_type.upper()})
- **Files Affected**: {len(service.files_affected)}
- **Estimated Changes**: {service.estimated_changes} lines
- **Complexity**: {service.complexity.value}
- **Confidence**: {service.confidence:.1%}
- **Patterns Found**: {', '.join(service.patterns_found[:5])}{'...' if len(service.patterns_found) > 5 else ''}

"""
        
        md += f"""## Change Estimates
- **Total Estimated Changes**: {self.total_estimated_changes:,} lines
- **Files to Modify**: {self.files_to_modify_count}
- **Estimated Duration**: {self.estimated_duration_minutes} minutes (if provided)

## Cross-File Dependencies
- **Total Dependencies**: {len(self.cross_file_dependencies)}
- Dependencies will be automatically handled during migration

## Infrastructure Files
- **IaC Files Found**: {len(self.infrastructure_files)}
"""
        for infra_file in self.infrastructure_files:
            md += f"- `{infra_file.file_path}` ({infra_file.file_type})\n"
        
        md += f"""
## Risk Assessment
- **Confidence Score**: {self.confidence_score:.1%}
- **Overall Risk**: {self.overall_risk.value.upper()}
"""
        if self.risks:
            md += "\n### Identified Risks\n"
            for risk in self.risks:
                md += f"- {risk}\n"
        
        md += f"""
## Test Strategy
- **Existing Tests Found**: {'Yes' if self.existing_tests_found else 'No'}
"""
        if self.test_framework:
            md += f"- **Test Framework**: {self.test_framework}\n"
        if self.test_files:
            md += f"- **Test Files**: {len(self.test_files)}\n"
        
        md += f"""
## Recommended Services to Migrate
{', '.join(self.recommended_services) if self.recommended_services else 'All detected services'}

---
*This report was generated automatically by the Universal Cloud Refactor Agent*
"""
        return md
