"""
Repository Entity

Architectural Intent:
- Represents a Git repository to be migrated
- Encapsulates repository metadata, Git provider info, and migration state
- Provides methods for repository analysis and migration tracking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class GitProvider(Enum):
    """Supported Git providers"""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    UNKNOWN = "unknown"


class RepositoryStatus(Enum):
    """Repository migration status"""
    ANALYZING = "analyzing"
    MAR_GENERATED = "mar_generated"
    MIGRATING = "migrating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Repository:
    """
    Repository Aggregate Root
    
    Invariants:
    - Must have a valid repository URL
    - Must have a valid branch name
    - Provider must be detected or specified
    """
    id: str
    url: str
    branch: str
    provider: GitProvider
    local_path: Optional[str] = None  # Path where repository is cloned
    languages: List[str] = field(default_factory=list)  # Detected languages
    total_files: int = 0
    total_lines: int = 0
    status: RepositoryStatus = RepositoryStatus.ANALYZING
    created_at: datetime = field(default_factory=datetime.now)
    analyzed_at: Optional[datetime] = None
    migrated_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def update_status(self, new_status: RepositoryStatus) -> 'Repository':
        """Returns a new repository with updated status"""
        return Repository(
            id=self.id,
            url=self.url,
            branch=self.branch,
            provider=self.provider,
            local_path=self.local_path,
            languages=self.languages,
            total_files=self.total_files,
            total_lines=self.total_lines,
            status=new_status,
            created_at=self.created_at,
            analyzed_at=self.analyzed_at,
            migrated_at=self.migrated_at,
            metadata=self.metadata
        )
    
    def mark_analyzed(self) -> 'Repository':
        """Mark repository as analyzed"""
        return Repository(
            id=self.id,
            url=self.url,
            branch=self.branch,
            provider=self.provider,
            local_path=self.local_path,
            languages=self.languages,
            total_files=self.total_files,
            total_lines=self.total_lines,
            status=self.status,
            created_at=self.created_at,
            analyzed_at=datetime.now(),
            migrated_at=self.migrated_at,
            metadata=self.metadata
        )
    
    def mark_migrated(self) -> 'Repository':
        """Mark repository as migrated"""
        return Repository(
            id=self.id,
            url=self.url,
            branch=self.branch,
            provider=self.provider,
            local_path=self.local_path,
            languages=self.languages,
            total_files=self.total_files,
            total_lines=self.total_lines,
            status=RepositoryStatus.COMPLETED,
            created_at=self.created_at,
            analyzed_at=self.analyzed_at,
            migrated_at=datetime.now(),
            metadata=self.metadata
        )
