"""
Git Adapter

Architectural Intent:
- Provides abstraction for Git operations across multiple providers
- Supports GitHub, GitLab, and Bitbucket
- Handles repository cloning, branch operations, and PR creation
"""

import os
import re
import tempfile
import subprocess
from typing import Optional, Dict, List
from enum import Enum
from dataclasses import dataclass

from domain.entities.repository import GitProvider, Repository


class GitAdapterError(Exception):
    """Base exception for Git adapter errors"""
    pass


class AuthenticationError(GitAdapterError):
    """Authentication failed"""
    pass


class RepositoryNotFoundError(GitAdapterError):
    """Repository not found"""
    pass


@dataclass
class GitCredentials:
    """Git credentials for authentication"""
    provider: GitProvider
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None


class GitAdapter:
    """
    Git Adapter for repository operations
    
    Supports multiple Git providers and handles cloning, branching, and PR operations.
    """
    
    def __init__(self, credentials: Optional[GitCredentials] = None):
        self.credentials = credentials
        self.temp_dir = tempfile.mkdtemp(prefix="refactor_repo_")
    
    def detect_provider(self, url: str) -> GitProvider:
        """Detect Git provider from URL"""
        url_lower = url.lower()
        if 'github.com' in url_lower:
            return GitProvider.GITHUB
        elif 'gitlab.com' in url_lower or 'gitlab' in url_lower:
            return GitProvider.GITLAB
        elif 'bitbucket.org' in url_lower or 'bitbucket' in url_lower:
            return GitProvider.BITBUCKET
        else:
            return GitProvider.UNKNOWN
    
    def normalize_url(self, url: str, provider: GitProvider) -> str:
        """Normalize Git URL for cloning"""
        # Remove .git suffix if present
        url = url.rstrip('.git')
        
        # Convert HTTPS to SSH if credentials have SSH key
        if self.credentials and self.credentials.ssh_key_path:
            if provider == GitProvider.GITHUB:
                url = url.replace('https://github.com/', 'git@github.com:')
            elif provider == GitProvider.GITLAB:
                url = url.replace('https://gitlab.com/', 'git@gitlab.com:')
            elif provider == GitProvider.BITBUCKET:
                url = url.replace('https://bitbucket.org/', 'git@bitbucket.org:')
        
        return url
    
    def clone_repository(self, url: str, branch: str = "main", target_dir: Optional[str] = None) -> str:
        """
        Clone a Git repository
        
        Args:
            url: Repository URL
            branch: Branch to clone
            target_dir: Target directory (optional, uses temp if not provided)
            
        Returns:
            Path to cloned repository
        """
        provider = self.detect_provider(url)
        normalized_url = self.normalize_url(url, provider)
        
        if target_dir is None:
            repo_name = self._extract_repo_name(url)
            target_dir = os.path.join(self.temp_dir, repo_name)
        
        # Prepare authentication
        env = os.environ.copy()
        if self.credentials:
            if self.credentials.token:
                if provider == GitProvider.GITHUB:
                    normalized_url = normalized_url.replace('https://', f'https://{self.credentials.token}@')
                elif provider == GitProvider.GITLAB:
                    normalized_url = normalized_url.replace('https://', f'https://oauth2:{self.credentials.token}@')
                elif provider == GitProvider.BITBUCKET:
                    if self.credentials.username and self.credentials.password:
                        normalized_url = normalized_url.replace('https://', f'https://{self.credentials.username}:{self.credentials.password}@')
            
            if self.credentials.ssh_key_path:
                env['GIT_SSH_COMMAND'] = f'ssh -i {self.credentials.ssh_key_path} -o StrictHostKeyChecking=no'
        
        try:
            # Clone repository
            cmd = ['git', 'clone', '--branch', branch, '--depth', '1', normalized_url, target_dir]
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr
                if 'Authentication failed' in error_msg or 'Permission denied' in error_msg:
                    raise AuthenticationError(f"Authentication failed for {url}: {error_msg}")
                elif 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                    raise RepositoryNotFoundError(f"Repository not found: {url}")
                else:
                    raise GitAdapterError(f"Failed to clone repository: {error_msg}")
            
            return target_dir
            
        except subprocess.TimeoutExpired:
            raise GitAdapterError(f"Timeout while cloning repository: {url}")
        except Exception as e:
            raise GitAdapterError(f"Error cloning repository: {str(e)}")
    
    def create_branch(self, repo_path: str, branch_name: str, base_branch: str = "main") -> None:
        """Create a new branch from base branch"""
        try:
            # Checkout base branch first
            subprocess.run(
                ['git', 'checkout', base_branch],
                cwd=repo_path,
                capture_output=True,
                check=True
            )
            
            # Create and checkout new branch
            subprocess.run(
                ['git', 'checkout', '-b', branch_name],
                cwd=repo_path,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise GitAdapterError(f"Failed to create branch: {e.stderr.decode()}")
    
    def commit_changes(self, repo_path: str, message: str, files: Optional[List[str]] = None) -> None:
        """Commit changes to repository"""
        try:
            # Add files
            if files:
                subprocess.run(
                    ['git', 'add'] + files,
                    cwd=repo_path,
                    capture_output=True,
                    check=True
                )
            else:
                subprocess.run(
                    ['git', 'add', '.'],
                    cwd=repo_path,
                    capture_output=True,
                    check=True
                )
            
            # Commit
            subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=repo_path,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise GitAdapterError(f"Failed to commit changes: {e.stderr.decode()}")
    
    def push_branch(self, repo_path: str, branch_name: str, remote: str = "origin") -> None:
        """Push branch to remote"""
        try:
            subprocess.run(
                ['git', 'push', '-u', remote, branch_name],
                cwd=repo_path,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise GitAdapterError(f"Failed to push branch: {e.stderr.decode()}")
    
    def get_repository_info(self, repo_path: str) -> Dict[str, str]:
        """Get repository information"""
        try:
            # Get remote URL
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            
            # Get current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            
            # Get commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = result.stdout.strip()
            
            return {
                'remote_url': remote_url,
                'current_branch': current_branch,
                'commit_hash': commit_hash
            }
        except subprocess.CalledProcessError as e:
            raise GitAdapterError(f"Failed to get repository info: {e.stderr.decode()}")
    
    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL"""
        # Remove protocol and .git suffix
        url = url.replace('https://', '').replace('http://', '').replace('git@', '')
        url = url.rstrip('.git')
        
        # Extract repo name (last part after /)
        parts = url.split('/')
        if len(parts) >= 2:
            repo_name = parts[-1]
            # Remove any special characters
            repo_name = re.sub(r'[^a-zA-Z0-9_-]', '_', repo_name)
            return repo_name
        return 'repository'
    
    def cleanup(self, repo_path: Optional[str] = None) -> None:
        """Clean up cloned repository"""
        import shutil
        if repo_path:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path, ignore_errors=True)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class GitHubAdapter(GitAdapter):
    """GitHub-specific adapter with API support"""
    
    def __init__(self, credentials: Optional[GitCredentials] = None):
        super().__init__(credentials)
        self.api_base = "https://api.github.com"
    
    def create_pull_request(self, repo_url: str, title: str, body: str, 
                           head_branch: str, base_branch: str = "main") -> Dict:
        """
        Create a Pull Request using GitHub API
        
        Returns:
            Dict with PR URL and number
        """
        # Extract owner and repo from URL
        owner, repo = self._parse_github_url(repo_url)
        
        if not self.credentials or not self.credentials.token:
            raise AuthenticationError("GitHub token required for PR creation")
        
        import requests
        
        url = f"{self.api_base}/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"token {self.credentials.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            pr_data = response.json()
            return {
                "pr_url": pr_data.get("html_url"),
                "pr_number": pr_data.get("number"),
                "pr_id": pr_data.get("id")
            }
        except requests.exceptions.RequestException as e:
            raise GitAdapterError(f"Failed to create GitHub PR: {str(e)}")
    
    def _parse_github_url(self, url: str) -> tuple:
        """Parse GitHub URL to extract owner and repo"""
        # Remove protocol and .git suffix
        url = url.replace('https://github.com/', '').replace('http://github.com/', '')
        url = url.replace('git@github.com:', '').rstrip('.git')
        
        parts = url.split('/')
        if len(parts) >= 2:
            return parts[0], parts[1]
        raise ValueError(f"Invalid GitHub URL: {url}")


class GitLabAdapter(GitAdapter):
    """GitLab-specific adapter with API support"""
    
    def __init__(self, credentials: Optional[GitCredentials] = None):
        super().__init__(credentials)
        # Detect GitLab instance (gitlab.com or self-hosted)
        self.api_base = "https://gitlab.com/api/v4"
    
    def create_merge_request(self, repo_url: str, title: str, description: str,
                            source_branch: str, target_branch: str = "main") -> Dict:
        """
        Create a Merge Request using GitLab API
        
        Returns:
            Dict with MR URL and IID
        """
        # Extract project path from URL
        project_path = self._parse_gitlab_url(repo_url)
        
        if not self.credentials or not self.credentials.token:
            raise AuthenticationError("GitLab token required for MR creation")
        
        import requests
        
        url = f"{self.api_base}/projects/{project_path}/merge_requests"
        headers = {
            "PRIVATE-TOKEN": self.credentials.token
        }
        data = {
            "title": title,
            "description": description,
            "source_branch": source_branch,
            "target_branch": target_branch
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            mr_data = response.json()
            return {
                "mr_url": mr_data.get("web_url"),
                "mr_iid": mr_data.get("iid"),
                "mr_id": mr_data.get("id")
            }
        except requests.exceptions.RequestException as e:
            raise GitAdapterError(f"Failed to create GitLab MR: {str(e)}")
    
    def _parse_gitlab_url(self, url: str) -> str:
        """Parse GitLab URL to extract project path"""
        # Remove protocol and .git suffix
        url = url.replace('https://gitlab.com/', '').replace('http://gitlab.com/', '')
        url = url.replace('git@gitlab.com:', '').rstrip('.git')
        
        # URL encode the project path
        from urllib.parse import quote
        return quote(url, safe='/')


class BitbucketAdapter(GitAdapter):
    """Bitbucket-specific adapter with API support"""
    
    def __init__(self, credentials: Optional[GitCredentials] = None):
        super().__init__(credentials)
        self.api_base = "https://api.bitbucket.org/2.0"
    
    def create_pull_request(self, repo_url: str, title: str, description: str,
                           source_branch: str, target_branch: str = "main") -> Dict:
        """
        Create a Pull Request using Bitbucket API
        
        Returns:
            Dict with PR URL and ID
        """
        # Extract workspace and repo from URL
        workspace, repo = self._parse_bitbucket_url(repo_url)
        
        if not self.credentials or not self.credentials.username or not self.credentials.password:
            raise AuthenticationError("Bitbucket username and password/app_password required")
        
        import requests
        from requests.auth import HTTPBasicAuth
        
        url = f"{self.api_base}/repositories/{workspace}/{repo}/pullrequests"
        auth = HTTPBasicAuth(self.credentials.username, self.credentials.password)
        data = {
            "title": title,
            "description": description,
            "source": {
                "branch": {
                    "name": source_branch
                }
            },
            "destination": {
                "branch": {
                    "name": target_branch
                }
            }
        }
        
        try:
            response = requests.post(url, json=data, auth=auth, timeout=30)
            response.raise_for_status()
            
            pr_data = response.json()
            return {
                "pr_url": pr_data.get("links", {}).get("html", {}).get("href"),
                "pr_id": pr_data.get("id")
            }
        except requests.exceptions.RequestException as e:
            raise GitAdapterError(f"Failed to create Bitbucket PR: {str(e)}")
    
    def _parse_bitbucket_url(self, url: str) -> tuple:
        """Parse Bitbucket URL to extract workspace and repo"""
        # Remove protocol and .git suffix
        url = url.replace('https://bitbucket.org/', '').replace('http://bitbucket.org/', '')
        url = url.replace('git@bitbucket.org:', '').rstrip('.git')
        
        parts = url.split('/')
        if len(parts) >= 2:
            return parts[0], parts[1]
        raise ValueError(f"Invalid Bitbucket URL: {url}")


def create_git_adapter(provider: GitProvider, credentials: Optional[GitCredentials] = None) -> GitAdapter:
    """Factory function to create appropriate Git adapter"""
    if provider == GitProvider.GITHUB:
        return GitHubAdapter(credentials)
    elif provider == GitProvider.GITLAB:
        return GitLabAdapter(credentials)
    elif provider == GitProvider.BITBUCKET:
        return BitbucketAdapter(credentials)
    else:
        return GitAdapter(credentials)
