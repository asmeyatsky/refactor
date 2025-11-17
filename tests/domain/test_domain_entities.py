"""
Domain Layer Tests

Testing the domain entities, services, and value objects
following the architectural intent and ensuring all business rules are enforced.
"""

import unittest
from datetime import datetime
from unittest.mock import Mock

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan, RefactoringTask, TaskStatus
from domain.services import RefactoringDomainService
from domain.value_objects import MigrationType, RefactoringResult


class TestCodebase(unittest.TestCase):
    """Test cases for the Codebase entity"""
    
    def test_codebase_creation(self):
        """Test that Codebase entity can be created with valid parameters"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py", "file2.py"],
            dependencies={"boto3": "1.26.0"},
            created_at=datetime.now()
        )
        
        self.assertEqual(codebase.id, "test-id")
        self.assertEqual(codebase.language, ProgrammingLanguage.PYTHON)
        self.assertEqual(len(codebase.files), 2)
        self.assertEqual(codebase.dependencies["boto3"], "1.26.0")
    
    def test_codebase_immutable(self):
        """Test that Codebase is immutable"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py", "file2.py"],
            dependencies={"boto3": "1.26.0"},
            created_at=datetime.now()
        )
        
        # Attempting to modify should raise an exception
        with self.assertRaises(Exception):
            codebase.id = "new-id"
    
    def test_get_aws_s3_files(self):
        """Test that get_aws_s3_files works correctly"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["s3_client.py", "regular_file.py"],
            dependencies={"boto3": "1.26.0"},
            created_at=datetime.now()
        )
        
        # Since the method currently only checks for 's3' in filename,
        # this should return the s3_client.py file
        s3_files = codebase.get_aws_s3_files()
        self.assertIn("s3_client.py", s3_files)


class TestRefactoringPlan(unittest.TestCase):
    """Test cases for the RefactoringPlan entity"""
    
    def setUp(self):
        self.tasks = [
            RefactoringTask(
                id="task1",
                description="Test task 1",
                file_path="file1.py",
                operation="replace_s3_with_gcs"
            ),
            RefactoringTask(
                id="task2",
                description="Test task 2",
                file_path="file2.py",
                operation="replace_s3_with_gcs",
                status=TaskStatus.COMPLETED
            )
        ]
        
        self.plan = RefactoringPlan(
            id="plan-test",
            codebase_id="codebase-test",
            tasks=self.tasks,
            created_at=datetime.now()
        )
    
    def test_plan_creation(self):
        """Test that RefactoringPlan can be created with valid parameters"""
        self.assertEqual(self.plan.id, "plan-test")
        self.assertEqual(self.plan.codebase_id, "codebase-test")
        self.assertEqual(len(self.plan.tasks), 2)
    
    def test_get_pending_tasks(self):
        """Test that get_pending_tasks returns only pending tasks"""
        pending_tasks = self.plan.get_pending_tasks()
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0].id, "task1")
        self.assertEqual(pending_tasks[0].status, TaskStatus.PENDING)
    
    def test_get_completed_tasks(self):
        """Test that get_completed_tasks returns only completed tasks"""
        completed_tasks = self.plan.get_completed_tasks()
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0].id, "task2")
        self.assertEqual(completed_tasks[0].status, TaskStatus.COMPLETED)
    
    def test_plan_executable_when_no_failed_tasks(self):
        """Test that plan is executable when no tasks are failed"""
        self.assertTrue(self.plan.is_executable())
    
    def test_plan_not_executable_when_has_failed_tasks(self):
        """Test that plan is not executable when it has failed tasks"""
        failed_task = RefactoringTask(
            id="task3",
            description="Failed task",
            file_path="file3.py",
            operation="replace_s3_with_gcs",
            status=TaskStatus.FAILED,
            error="Test error"
        )
        
        plan_with_failed = RefactoringPlan(
            id="plan-with-failed",
            codebase_id="codebase-test",
            tasks=self.tasks + [failed_task],
            created_at=datetime.now()
        )
        
        self.assertFalse(plan_with_failed.is_executable())
    
    def test_mark_task_in_progress(self):
        """Test marking a task as in progress"""
        updated_plan = self.plan.mark_task_in_progress("task1")
        task1 = next(t for t in updated_plan.tasks if t.id == "task1")
        self.assertEqual(task1.status, TaskStatus.IN_PROGRESS)
    
    def test_mark_task_completed(self):
        """Test marking a task as completed"""
        updated_plan = self.plan.mark_task_in_progress("task1")
        updated_plan = updated_plan.mark_task_completed("task1")
        task1 = next(t for t in updated_plan.tasks if t.id == "task1")
        self.assertEqual(task1.status, TaskStatus.COMPLETED)
    
    def test_mark_task_failed(self):
        """Test marking a task as failed"""
        updated_plan = self.plan.mark_task_failed("task1", "Test error")
        task1 = next(t for t in updated_plan.tasks if t.id == "task1")
        self.assertEqual(task1.status, TaskStatus.FAILED)
        self.assertEqual(task1.error, "Test error")


class TestRefactoringDomainService(unittest.TestCase):
    """Test cases for the RefactoringDomainService"""
    
    def setUp(self):
        self.code_analyzer = Mock()
        self.llm_provider = Mock()
        self.ast_transformer = Mock()
        
        self.service = RefactoringDomainService(
            code_analyzer=self.code_analyzer,
            llm_provider=self.llm_provider,
            ast_transformer=self.ast_transformer
        )
        
        self.codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["s3_file.py", "regular_file.py"],
            dependencies={"boto3": "1.26.0"},
            created_at=datetime.now()
        )
    
    def test_create_refactoring_plan(self):
        """Test creating a refactoring plan"""
        # Mock the code analyzer to return S3 files
        self.code_analyzer.identify_aws_s3_usage.return_value = ["s3_file.py"]
        
        plan = self.service.create_refactoring_plan(self.codebase)
        
        # Verify the plan was created correctly
        self.assertEqual(plan.codebase_id, "test-id")
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].file_path, "s3_file.py")
        self.assertEqual(plan.tasks[0].operation, "replace_aws_s3_with_gcs")
        
        # Verify that the analyzer was called
        self.code_analyzer.identify_aws_s3_usage.assert_called_once_with(self.codebase)


if __name__ == '__main__':
    unittest.main()