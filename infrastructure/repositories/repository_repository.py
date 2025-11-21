"""
Repository Repository Adapter

Architectural Intent:
- Implements repository persistence for Git repositories
- Handles storage and retrieval of repository metadata
"""

import json
import os
from typing import Optional
from datetime import datetime

from domain.entities.repository import Repository, GitProvider, RepositoryStatus


class RepositoryRepositoryAdapter:
    """Implementation of repository persistence using JSON files"""
    
    def __init__(self, storage_path: str = None):
        try:
            from config import config
            self.storage_path = storage_path or getattr(config, 'REPOSITORY_STORAGE_PATH', '/tmp/repositories')
        except (ImportError, AttributeError):
            self.storage_path = storage_path or '/tmp/repositories'
        os.makedirs(self.storage_path, exist_ok=True)
    
    def save(self, repository: Repository) -> None:
        """Save a repository to JSON file"""
        file_path = os.path.join(self.storage_path, f"{repository.id}.json")
        data = {
            "id": repository.id,
            "url": repository.url,
            "branch": repository.branch,
            "provider": repository.provider.value,
            "local_path": repository.local_path,
            "languages": repository.languages,
            "total_files": repository.total_files,
            "total_lines": repository.total_lines,
            "status": repository.status.value,
            "created_at": repository.created_at.isoformat(),
            "analyzed_at": repository.analyzed_at.isoformat() if repository.analyzed_at else None,
            "migrated_at": repository.migrated_at.isoformat() if repository.migrated_at else None,
            "metadata": repository.metadata
        }
        
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
    
    def load(self, repository_id: str) -> Optional[Repository]:
        """Load a repository from JSON file"""
        file_path = os.path.join(self.storage_path, f"{repository_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        return Repository(
            id=data["id"],
            url=data["url"],
            branch=data["branch"],
            provider=GitProvider(data["provider"]),
            local_path=data.get("local_path"),
            languages=data.get("languages", []),
            total_files=data.get("total_files", 0),
            total_lines=data.get("total_lines", 0),
            status=RepositoryStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            analyzed_at=datetime.fromisoformat(data["analyzed_at"]) if data.get("analyzed_at") else None,
            migrated_at=datetime.fromisoformat(data["migrated_at"]) if data.get("migrated_at") else None,
            metadata=data.get("metadata", {})
        )
    
    def find_by_url(self, url: str, branch: str) -> Optional[Repository]:
        """Find repository by URL and branch"""
        # Simple implementation: scan all files
        # In production, use a database or index
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                repo = self.load(filename[:-5])  # Remove .json extension
                if repo and repo.url == url and repo.branch == branch:
                    return repo
        return None
