"""
Refactoring Plan Entity

Architectural Intent:
- Represents the plan for refactoring a codebase
- Contains the tasks to be executed in sequence
- Tracks the progress and status of the refactoring
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RefactoringTask:
    """A single refactoring task"""
    id: str
    description: str
    file_path: str
    operation: str  # e.g., "replace_s3_with_gcs"
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass(frozen=True)
class RefactoringPlan:
    """
    Refactoring Plan Aggregate Root
    
    Invariants:
    - Must have at least one task
    - All tasks must have unique IDs
    - Cannot be executed if any task is in FAILED state
    """
    id: str
    codebase_id: str
    tasks: List[RefactoringTask]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def get_pending_tasks(self) -> List[RefactoringTask]:
        """Returns all pending tasks"""
        return [task for task in self.tasks if task.status == TaskStatus.PENDING]

    def get_completed_tasks(self) -> List[RefactoringTask]:
        """Returns all completed tasks"""
        return [task for task in self.tasks if task.status == TaskStatus.COMPLETED]

    def get_failed_tasks(self) -> List[RefactoringTask]:
        """Returns all failed tasks"""
        return [task for task in self.tasks if task.status == TaskStatus.FAILED]

    def is_executable(self) -> bool:
        """Check if the plan can be executed"""
        return len(self.get_failed_tasks()) == 0

    def mark_task_in_progress(self, task_id: str) -> 'RefactoringPlan':
        """Returns a new plan with the specified task marked as IN_PROGRESS"""
        updated_tasks = []
        for task in self.tasks:
            if task.id == task_id:
                updated_tasks.append(RefactoringTask(
                    id=task.id,
                    description=task.description,
                    file_path=task.file_path,
                    operation=task.operation,
                    status=TaskStatus.IN_PROGRESS
                ))
            else:
                updated_tasks.append(task)
        
        return RefactoringPlan(
            id=self.id,
            codebase_id=self.codebase_id,
            tasks=updated_tasks,
            created_at=self.created_at,
            started_at=self.started_at or datetime.now(),
            completed_at=self.completed_at,
            metadata=self.metadata
        )

    def mark_task_completed(self, task_id: str) -> 'RefactoringPlan':
        """Returns a new plan with the specified task marked as COMPLETED"""
        updated_tasks = []
        for task in self.tasks:
            if task.id == task_id:
                updated_tasks.append(RefactoringTask(
                    id=task.id,
                    description=task.description,
                    file_path=task.file_path,
                    operation=task.operation,
                    status=TaskStatus.COMPLETED,
                    completed_at=datetime.now()
                ))
            else:
                updated_tasks.append(task)
        
        # Check if all tasks are completed
        all_completed = all(t.status == TaskStatus.COMPLETED for t in updated_tasks)
        if all_completed and self.completed_at is None:
            completed_at = datetime.now()
        else:
            completed_at = self.completed_at
        
        return RefactoringPlan(
            id=self.id,
            codebase_id=self.codebase_id,
            tasks=updated_tasks,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=completed_at,
            metadata=self.metadata
        )

    def mark_task_failed(self, task_id: str, error: str) -> 'RefactoringPlan':
        """Returns a new plan with the specified task marked as FAILED"""
        updated_tasks = []
        for task in self.tasks:
            if task.id == task_id:
                updated_tasks.append(RefactoringTask(
                    id=task.id,
                    description=task.description,
                    file_path=task.file_path,
                    operation=task.operation,
                    status=TaskStatus.FAILED,
                    error=error
                ))
            else:
                updated_tasks.append(task)
        
        return RefactoringPlan(
            id=self.id,
            codebase_id=self.codebase_id,
            tasks=updated_tasks,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            metadata=self.metadata
        )