"""
Analyze Repository Use Case

Architectural Intent:
- Orchestrates repository analysis workflow
- Clones repository, builds dependency graph, and generates MAR
"""

import os
import uuid
from typing import Optional, Dict
from datetime import datetime

from domain.entities.repository import Repository, GitProvider, RepositoryStatus
from domain.value_objects.mar import MigrationAssessmentReport
from infrastructure.adapters.git_adapter import GitAdapter, GitCredentials, create_git_adapter
from infrastructure.adapters.mar_generator import MARGenerator
from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter


class AnalyzeRepositoryUseCase:
    """
    Use case for analyzing a Git repository and generating MAR
    """
    
    def __init__(self,
                 git_adapter: Optional[GitAdapter] = None,
                 mar_generator: Optional[MARGenerator] = None,
                 repository_repo: Optional[RepositoryRepositoryAdapter] = None):
        self.git_adapter = git_adapter or GitAdapter()
        self.mar_generator = mar_generator or MARGenerator()
        self.repository_repo = repository_repo or RepositoryRepositoryAdapter()
    
    def execute(self, repository_url: str, branch: str = "main",
                credentials: Optional[GitCredentials] = None) -> Dict:
        """
        Analyze repository and generate MAR
        
        Args:
            repository_url: Git repository URL
            branch: Branch to analyze
            credentials: Optional Git credentials
            
        Returns:
            Dict with repository_id, mar, and repository object
        """
        # Detect provider
        provider = self.git_adapter.detect_provider(repository_url)
        
        # Create repository entity
        repository_id = str(uuid.uuid4())
        repository = Repository(
            id=repository_id,
            url=repository_url,
            branch=branch,
            provider=provider,
            status=RepositoryStatus.ANALYZING
        )
        
        # Save repository
        self.repository_repo.save(repository)
        
        try:
            # Clone repository
            if credentials:
                self.git_adapter.credentials = credentials
            
            local_path = self.git_adapter.clone_repository(repository_url, branch)
            
            # Update repository with local path
            repository = Repository(
                id=repository.id,
                url=repository.url,
                branch=repository.branch,
                provider=repository.provider,
                local_path=local_path,
                languages=repository.languages,
                total_files=repository.total_files,
                total_lines=repository.total_lines,
                status=repository.status,
                created_at=repository.created_at,
                analyzed_at=repository.analyzed_at,
                migrated_at=repository.migrated_at,
                metadata=repository.metadata
            )
            
            # Generate MAR
            mar = self.mar_generator.generate_mar(
                repository_path=local_path,
                repository_id=repository_id,
                repository_url=repository_url,
                branch=branch
            )
            
            # Update repository with analysis results
            repository = Repository(
                id=repository.id,
                url=repository.url,
                branch=repository.branch,
                provider=repository.provider,
                local_path=local_path,
                languages=mar.languages_detected,
                total_files=mar.total_files,
                total_lines=mar.total_lines,
                status=RepositoryStatus.MAR_GENERATED,
                created_at=repository.created_at,
                analyzed_at=datetime.now(),
                migrated_at=repository.migrated_at,
                metadata=repository.metadata
            )
            
            # Save updated repository
            self.repository_repo.save(repository)
            
            return {
                'repository_id': repository_id,
                'repository': repository,
                'mar': mar,
                'success': True
            }
            
        except Exception as e:
            # Update repository status to failed
            repository = repository.update_status(RepositoryStatus.FAILED)
            repository.metadata['error'] = str(e)
            self.repository_repo.save(repository)
            
            return {
                'repository_id': repository_id,
                'repository': repository,
                'mar': None,
                'success': False,
                'error': str(e)
            }
