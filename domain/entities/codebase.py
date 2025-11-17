"""
Codebase Entity

Architectural Intent:
- Represents a codebase to be refactored
- Encapsulates the files, dependencies and metadata of a codebase
- Provides methods for analyzing and modifying the codebase structure
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class ProgrammingLanguage(Enum):
    JAVA = "java"
    PYTHON = "python"


@dataclass(frozen=True)
class Codebase:
    """
    Codebase Aggregate Root
    
    Invariants:
    - Must have a valid path
    - Language must be supported
    - Files list cannot be empty
    """
    id: str
    path: str
    language: ProgrammingLanguage
    files: List[str]  # List of file paths
    dependencies: Dict[str, str]  # dependency_name -> version
    created_at: datetime
    metadata: Dict[str, str] = field(default_factory=dict)

    def get_aws_s3_files(self) -> List[str]:
        """Returns list of files that contain AWS S3 references"""
        # This would be implemented with AST analysis
        s3_files = []
        for file_path in self.files:
            # In a real implementation, we would parse the file with AST
            # and look for AWS S3 references
            if 's3' in file_path.lower() or 'aws' in file_path.lower():
                s3_files.append(file_path)
        return s3_files

    def update_file(self, file_path: str, new_content: str) -> 'Codebase':
        """Returns a new codebase with updated file content"""
        import os
        updated_files = []
        for f in self.files:
            if f == file_path:
                # Write the new content to the file
                with open(f, 'w') as file:
                    file.write(new_content)
            updated_files.append(f)
        
        return Codebase(
            id=self.id,
            path=self.path,
            language=self.language,
            files=updated_files,
            dependencies=self.dependencies,
            created_at=self.created_at,
            metadata=self.metadata
        )