"""
Infrastructure Layer - Repository Implementations

Architectural Intent:
- Implement the interfaces defined in the domain layer
- Handle persistence, external API calls, and infrastructure concerns
- Provide concrete implementations for file operations, code analysis, etc.
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan
from domain.ports import (
    FileRepositoryPort, CodebaseRepositoryPort, PlanRepositoryPort
)


class FileRepositoryAdapter(FileRepositoryPort):
    """Implementation of FileRepositoryPort using the local file system"""
    
    def __init__(self, base_path: str = None):
        try:
            from config import config
            self.base_path = base_path or config.BACKUP_STORAGE_PATH
        except ImportError:
            self.base_path = base_path or "/tmp/refactor_backups"
        os.makedirs(self.base_path, exist_ok=True)

    def read_file(self, file_path: str) -> str:
        """Read content from a file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file"""
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def create_backup(self, file_path: str) -> str:
        """Create a backup of a file and return backup path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        backup_path = os.path.join(
            self.base_path,
            f"{name}_backup_{timestamp}{ext}"
        )
        
        content = self.read_file(file_path)
        self.write_file(backup_path, content)
        
        return backup_path


class CodebaseRepositoryAdapter(CodebaseRepositoryPort):
    """Implementation of CodebaseRepositoryPort using JSON files for persistence"""
    
    def __init__(self, storage_path: str = None):
        try:
            from config import config
            self.storage_path = storage_path or config.CODEBASE_STORAGE_PATH
        except ImportError:
            self.storage_path = storage_path or "/tmp/codebases"
        os.makedirs(self.storage_path, exist_ok=True)

    def save(self, codebase: Codebase) -> None:
        """Save a codebase to JSON file"""
        file_path = os.path.join(self.storage_path, f"{codebase.id}.json")
        data = {
            "id": codebase.id,
            "path": codebase.path,
            "language": codebase.language.value,
            "files": codebase.files,
            "dependencies": codebase.dependencies,
            "created_at": codebase.created_at.isoformat(),
            "metadata": codebase.metadata
        }
        
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)

    def load(self, codebase_id: str) -> Optional[Codebase]:
        """Load a codebase from JSON file"""
        file_path = os.path.join(self.storage_path, f"{codebase_id}.json")
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as file:
            data = json.load(file)
            
        return Codebase(
            id=data["id"],
            path=data["path"],
            language=ProgrammingLanguage(data["language"]),
            files=data["files"],
            dependencies=data["dependencies"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data["metadata"]
        )


class PlanRepositoryAdapter(PlanRepositoryPort):
    """Implementation of PlanRepositoryPort using JSON files for persistence"""
    
    def __init__(self, storage_path: str = None):
        try:
            from config import config
            self.storage_path = storage_path or config.PLAN_STORAGE_PATH
        except ImportError:
            self.storage_path = storage_path or "/tmp/plans"
        os.makedirs(self.storage_path, exist_ok=True)

    def save(self, plan: RefactoringPlan) -> None:
        """Save a refactoring plan to JSON file"""
        file_path = os.path.join(self.storage_path, f"{plan.id}.json")
        
        # Convert tasks to JSON-serializable format
        tasks_data = []
        for task in plan.tasks:
            task_data = {
                "id": task.id,
                "description": task.description,
                "file_path": task.file_path,
                "operation": task.operation,
                "status": task.status.value,
            }
            if task.error:
                task_data["error"] = task.error
            if task.completed_at:
                task_data["completed_at"] = task.completed_at.isoformat()
            
            tasks_data.append(task_data)
        
        data = {
            "id": plan.id,
            "codebase_id": plan.codebase_id,
            "tasks": tasks_data,
            "created_at": plan.created_at.isoformat(),
            "started_at": plan.started_at.isoformat() if plan.started_at else None,
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
            "metadata": plan.metadata
        }
        
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)

    def load(self, plan_id: str) -> Optional[RefactoringPlan]:
        """Load a refactoring plan from JSON file"""
        file_path = os.path.join(self.storage_path, f"{plan_id}.json")
        
        if not os.path.exists(file_path):
            return None
            
        from domain.entities.refactoring_plan import TaskStatus, RefactoringTask
        
        with open(file_path, 'r') as file:
            data = json.load(file)
            
        # Convert tasks back to RefactoringTask objects
        tasks = []
        for task_data in data["tasks"]:
            task = RefactoringTask(
                id=task_data["id"],
                description=task_data["description"],
                file_path=task_data["file_path"],
                operation=task_data["operation"],
                status=TaskStatus(task_data["status"]),
            )
            
            if "error" in task_data:
                task = RefactoringTask(
                    id=task.id,
                    description=task.description,
                    file_path=task.file_path,
                    operation=task.operation,
                    status=task.status,
                    error=task_data["error"]
                )
                
            if "completed_at" in task_data:
                task = RefactoringTask(
                    id=task.id,
                    description=task.description,
                    file_path=task.file_path,
                    operation=task.operation,
                    status=task.status,
                    completed_at=datetime.fromisoformat(task_data["completed_at"])
                )
                
            tasks.append(task)
        
        return RefactoringPlan(
            id=data["id"],
            codebase_id=data["codebase_id"],
            tasks=tasks,
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
            metadata=data["metadata"]
        )