"""
Pull Request Manager

Architectural Intent:
- Manages Pull Request creation across Git providers
- Handles branch creation, commits, and PR/MR opening
"""

from typing import Dict, Optional, List
from domain.entities.repository import Repository, GitProvider
from domain.value_objects.mar import MigrationAssessmentReport
from infrastructure.adapters.git_adapter import (
    GitAdapter, GitHubAdapter, GitLabAdapter, BitbucketAdapter,
    GitCredentials, create_git_adapter
)


class PRManager:
    """
    Manages Pull Request creation for migrated repositories
    """
    
    def __init__(self, git_adapter: Optional[GitAdapter] = None):
        self.git_adapter = git_adapter
    
    def create_migration_pr(self, repository: Repository, mar: MigrationAssessmentReport,
                           branch_name: Optional[str] = None) -> Dict:
        """
        Create a Pull Request with migrated changes
        
        Args:
            repository: Repository entity
            mar: Migration Assessment Report
            branch_name: Optional branch name (auto-generated if not provided)
            
        Returns:
            Dict with PR URL and details
        """
        if not repository.local_path:
            raise ValueError("Repository must be cloned before creating PR")
        
        # Generate branch name if not provided
        if not branch_name:
            branch_name = f"cloud-migration-{mar.generated_at.strftime('%Y%m%d-%H%M%S')}"
        
        # Get appropriate adapter
        adapter = create_git_adapter(repository.provider, self.git_adapter.credentials if self.git_adapter else None)
        
        try:
            # Create branch
            adapter.create_branch(repository.local_path, branch_name, repository.branch)
            
            # Commit all changes
            commit_message = f"""Cloud Migration: {', '.join([s.service_name for s in mar.services_detected[:5]])}

Migrated {len(mar.services_detected)} cloud service(s) to GCP:
{chr(10).join([f'- {s.service_name} ({s.service_type})' for s in mar.services_detected])}

Files changed: {mar.files_to_modify_count}
Total changes: {mar.total_estimated_changes:,} lines

See Migration Assessment Report (MAR) for details.
"""
            adapter.commit_changes(repository.local_path, commit_message)
            
            # Push branch
            adapter.push_branch(repository.local_path, branch_name)
            
            # Create PR/MR
            pr_title = f"Cloud Migration: {', '.join([s.service_name for s in mar.services_detected[:3]])} → GCP"
            pr_body = mar.to_markdown()
            
            if repository.provider == GitProvider.GITHUB:
                if isinstance(adapter, GitHubAdapter):
                    pr_result = adapter.create_pull_request(
                        repo_url=repository.url,
                        title=pr_title,
                        body=pr_body,
                        head_branch=branch_name,
                        base_branch=repository.branch
                    )
                    return {
                        'success': True,
                        'pr_url': pr_result.get('pr_url'),
                        'pr_number': pr_result.get('pr_number'),
                        'branch_name': branch_name
                    }
            elif repository.provider == GitProvider.GITLAB:
                if isinstance(adapter, GitLabAdapter):
                    mr_result = adapter.create_merge_request(
                        repo_url=repository.url,
                        title=pr_title,
                        description=pr_body,
                        source_branch=branch_name,
                        target_branch=repository.branch
                    )
                    return {
                        'success': True,
                        'pr_url': mr_result.get('mr_url'),
                        'mr_iid': mr_result.get('mr_iid'),
                        'branch_name': branch_name
                    }
            elif repository.provider == GitProvider.BITBUCKET:
                if isinstance(adapter, BitbucketAdapter):
                    pr_result = adapter.create_pull_request(
                        repo_url=repository.url,
                        title=pr_title,
                        description=pr_body,
                        source_branch=branch_name,
                        target_branch=repository.branch
                    )
                    return {
                        'success': True,
                        'pr_url': pr_result.get('pr_url'),
                        'pr_id': pr_result.get('pr_id'),
                        'branch_name': branch_name
                    }
            
            # If PR creation not supported or failed, return branch info
            return {
                'success': True,
                'branch_name': branch_name,
                'message': 'Branch created and pushed. Please create PR manually.',
                'pr_body': pr_body
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'branch_name': branch_name
            }
