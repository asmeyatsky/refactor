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
            
        Raises:
            ValueError: If repository_url is invalid
        """
        # Input validation
        if not repository_url or not isinstance(repository_url, str):
            raise ValueError("repository_url must be a non-empty string")
        
        repository_url = repository_url.strip()
        if not repository_url:
            raise ValueError("repository_url cannot be empty")
        
        if branch is not None and not isinstance(branch, str):
            raise ValueError("branch must be a string or None")
        
        # Detect provider
        try:
            provider = self.git_adapter.detect_provider(repository_url)
        except Exception as e:
            raise ValueError(f"Invalid repository URL: {str(e)}") from e
        
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
            
            # Auto-detect branch if not provided or empty
            # Handle both None and empty string cases
            if branch is None or (isinstance(branch, str) and branch.strip() == ""):
                try:
                    branch = self.git_adapter.get_default_branch(repository_url)
                    print(f"Auto-detected default branch: {branch}")
                except Exception as e:
                    print(f"Warning: Could not detect default branch, using 'main': {e}")
                    branch = "main"
            
            print(f"Cloning repository {repository_url} with branch {branch}")
            local_path = self.git_adapter.clone_repository(repository_url, branch)
            print(f"Successfully cloned to: {local_path}")
            
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
            import traceback
            error_traceback = traceback.format_exc()
            error_msg = str(e)
            
            # Log the error for debugging
            print(f"ERROR in AnalyzeRepositoryUseCase: {error_msg}")
            print(f"Traceback: {error_traceback}")
            
            # Update repository status to failed
            try:
                # Create a new repository object with failed status
                repository = Repository(
                    id=repository.id,
                    url=repository.url,
                    branch=repository.branch,
                    provider=repository.provider,
                    local_path=repository.local_path,
                    languages=repository.languages,
                    total_files=repository.total_files,
                    total_lines=repository.total_lines,
                    status=RepositoryStatus.FAILED,
                    created_at=repository.created_at,
                    analyzed_at=repository.analyzed_at,
                    migrated_at=repository.migrated_at,
                    metadata={**repository.metadata, 'error': error_msg}
                )
                self.repository_repo.save(repository)
            except Exception as save_error:
                print(f"ERROR saving failed repository: {save_error}")
            
            return {
                'repository_id': repository_id,
                'repository': repository,
                'mar': None,
                'success': False,
                'error': error_msg
            }
