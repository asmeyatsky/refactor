"""
Comprehensive Unit Tests for Domain Entities

This test suite provides extensive coverage for domain entities with
multiple test scenarios including edge cases, validation, and invariants.
"""

import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import Mock

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan, RefactoringTask, TaskStatus
from domain.services import RefactoringDomainService


class TestCodebaseComprehensive(unittest.TestCase):
    """Comprehensive test cases for Codebase entity"""
    
    def test_codebase_creation_with_all_fields(self):
        """Test creating codebase with all fields"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py", "file2.py"],
            dependencies={"boto3": "1.26.0", "requests": "2.28.0"},
            created_at=datetime.now(),
            metadata={"key": "value"}
        )
        
        self.assertEqual(codebase.id, "test-id")
        self.assertEqual(codebase.path, "/path/to/codebase")
        self.assertEqual(codebase.language, ProgrammingLanguage.PYTHON)
        self.assertEqual(len(codebase.files), 2)
        self.assertEqual(len(codebase.dependencies), 2)
        self.assertIn("key", codebase.metadata)
    
    def test_codebase_creation_minimal_fields(self):
        """Test creating codebase with minimal required fields"""
        codebase = Codebase(
            id="test-id",
            path="/path",
            language=ProgrammingLanguage.PYTHON,
            files=[],
            dependencies={},
            created_at=datetime.now()
        )
        
        self.assertEqual(codebase.id, "test-id")
        self.assertEqual(len(codebase.files), 0)
        self.assertEqual(len(codebase.dependencies), 0)
        self.assertEqual(len(codebase.metadata), 0)
    
    def test_codebase_immutability(self):
        """Test that Codebase is immutable (frozen dataclass)"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py"],
            dependencies={},
            created_at=datetime.now()
        )
        
        # Attempting to modify should raise an exception
        with self.assertRaises(Exception):
            codebase.id = "new-id"
        
        with self.assertRaises(Exception):
            codebase.path = "/new/path"
        
        with self.assertRaises(Exception):
            codebase.language = ProgrammingLanguage.JAVA
    
    def test_get_aws_s3_files_with_s3_in_filename(self):
        """Test get_aws_s3_files finds files with 's3' in filename"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["s3_client.py", "s3_utils.py", "regular_file.py"],
            dependencies={},
            created_at=datetime.now()
        )
        
        s3_files = codebase.get_aws_s3_files()
        self.assertIn("s3_client.py", s3_files)
        self.assertIn("s3_utils.py", s3_files)
        self.assertNotIn("regular_file.py", s3_files)
    
    def test_get_aws_s3_files_with_aws_in_filename(self):
        """Test get_aws_s3_files finds files with 'aws' in filename"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["aws_config.py", "regular_file.py"],
            dependencies={},
            created_at=datetime.now()
        )
        
        s3_files = codebase.get_aws_s3_files()
        self.assertIn("aws_config.py", s3_files)
    
    def test_get_aws_s3_files_case_insensitive(self):
        """Test get_aws_s3_files is case insensitive"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["S3_CLIENT.py", "AWS_UTILS.py", "regular_file.py"],
            dependencies={},
            created_at=datetime.now()
        )
        
        s3_files = codebase.get_aws_s3_files()
        self.assertIn("S3_CLIENT.py", s3_files)
        self.assertIn("AWS_UTILS.py", s3_files)
    
    def test_get_aws_s3_files_with_empty_list(self):
        """Test get_aws_s3_files with empty files list"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=[],
            dependencies={},
            created_at=datetime.now()
        )
        
        s3_files = codebase.get_aws_s3_files()
        self.assertEqual(len(s3_files), 0)
    
    def test_codebase_with_different_languages(self):
        """Test codebase creation with different programming languages"""
        languages = [
            ProgrammingLanguage.PYTHON,
            ProgrammingLanguage.JAVA,
            ProgrammingLanguage.CSHARP,
            ProgrammingLanguage.JAVASCRIPT,
            ProgrammingLanguage.GO
        ]
        
        for lang in languages:
            codebase = Codebase(
                id=f"test-{lang.value}",
                path="/path",
                language=lang,
                files=[],
                dependencies={},
                created_at=datetime.now()
            )
            self.assertEqual(codebase.language, lang)
    
    def test_codebase_update_file_creates_new_instance(self):
        """Test that update_file creates a new codebase instance"""
        codebase = Codebase(
            id="test-id",
            path="/path/to/codebase",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py"],
            dependencies={},
            created_at=datetime.now()
        )
        
        with mock.patch('builtins.open', mock.mock_open()):
            updated = codebase.update_file("file1.py", "new content")
        
        # Should return a new instance
        self.assertIsNot(updated, codebase)
        self.assertEqual(updated.id, codebase.id)


class TestRefactoringTaskComprehensive(unittest.TestCase):
    """Comprehensive test cases for RefactoringTask"""
    
    def test_task_creation_with_all_fields(self):
        """Test creating task with all fields"""
        task = RefactoringTask(
            id="task1",
            description="Test task",
            file_path="file.py",
            operation="migrate_s3_to_gcs",
            status=TaskStatus.PENDING,
            error=None,
            completed_at=None
        )
        
        self.assertEqual(task.id, "task1")
        self.assertEqual(task.description, "Test task")
        self.assertEqual(task.file_path, "file.py")
        self.assertEqual(task.operation, "migrate_s3_to_gcs")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIsNone(task.error)
        self.assertIsNone(task.completed_at)
    
    def test_task_creation_minimal_fields(self):
        """Test creating task with minimal fields"""
        task = RefactoringTask(
            id="task1",
            description="Test",
            file_path="file.py",
            operation="migrate"
        )
        
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIsNone(task.error)
        self.assertIsNone(task.completed_at)
    
    def test_task_immutability(self):
        """Test that RefactoringTask is immutable"""
        task = RefactoringTask(
            id="task1",
            description="Test",
            file_path="file.py",
            operation="migrate"
        )
        
        with self.assertRaises(Exception):
            task.id = "new-id"
        
        with self.assertRaises(Exception):
            task.status = TaskStatus.COMPLETED
    
    def test_task_with_failed_status(self):
        """Test task with failed status and error"""
        task = RefactoringTask(
            id="task1",
            description="Test",
            file_path="file.py",
            operation="migrate",
            status=TaskStatus.FAILED,
            error="Transformation failed"
        )
        
        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertEqual(task.error, "Transformation failed")
    
    def test_task_with_completed_status(self):
        """Test task with completed status"""
        completed_at = datetime.now()
        task = RefactoringTask(
            id="task1",
            description="Test",
            file_path="file.py",
            operation="migrate",
            status=TaskStatus.COMPLETED,
            completed_at=completed_at
        )
        
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.completed_at, completed_at)


class TestRefactoringPlanComprehensive(unittest.TestCase):
    """Comprehensive test cases for RefactoringPlan"""
    
    def setUp(self):
        self.tasks = [
            RefactoringTask(
                id="task1",
                description="Task 1",
                file_path="file1.py",
                operation="migrate_s3_to_gcs",
                status=TaskStatus.PENDING
            ),
            RefactoringTask(
                id="task2",
                description="Task 2",
                file_path="file2.py",
                operation="migrate_lambda_to_gcp",
                status=TaskStatus.COMPLETED
            ),
            RefactoringTask(
                id="task3",
                description="Task 3",
                file_path="file3.py",
                operation="migrate_dynamodb_to_gcp",
                status=TaskStatus.IN_PROGRESS
            )
        ]
        
        self.plan = RefactoringPlan(
            id="plan-test",
            codebase_id="codebase-test",
            tasks=self.tasks,
            created_at=datetime.now()
        )
    
    def test_plan_creation_with_all_fields(self):
        """Test creating plan with all fields"""
        started_at = datetime.now()
        completed_at = datetime.now()
        
        plan = RefactoringPlan(
            id="plan-test",
            codebase_id="codebase-test",
            tasks=self.tasks,
            created_at=datetime.now(),
            started_at=started_at,
            completed_at=completed_at,
            metadata={"key": "value"}
        )
        
        self.assertEqual(plan.id, "plan-test")
        self.assertEqual(plan.codebase_id, "codebase-test")
        self.assertEqual(len(plan.tasks), 3)
        self.assertEqual(plan.started_at, started_at)
        self.assertEqual(plan.completed_at, completed_at)
        self.assertIn("key", plan.metadata)
    
    def test_get_pending_tasks(self):
        """Test get_pending_tasks returns only pending tasks"""
        pending_tasks = self.plan.get_pending_tasks()
        
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0].id, "task1")
        self.assertEqual(pending_tasks[0].status, TaskStatus.PENDING)
    
    def test_get_completed_tasks(self):
        """Test get_completed_tasks returns only completed tasks"""
        completed_tasks = self.plan.get_completed_tasks()
        
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0].id, "task2")
        self.assertEqual(completed_tasks[0].status, TaskStatus.COMPLETED)
    
    def test_get_failed_tasks(self):
        """Test get_failed_tasks returns only failed tasks"""
        failed_task = RefactoringTask(
            id="task4",
            description="Failed task",
            file_path="file4.py",
            operation="migrate",
            status=TaskStatus.FAILED,
            error="Error message"
        )
        
        plan_with_failed = RefactoringPlan(
            id="plan-failed",
            codebase_id="codebase-test",
            tasks=self.tasks + [failed_task],
            created_at=datetime.now()
        )
        
        failed_tasks = plan_with_failed.get_failed_tasks()
        self.assertEqual(len(failed_tasks), 1)
        self.assertEqual(failed_tasks[0].id, "task4")
    
    def test_is_executable_with_no_failed_tasks(self):
        """Test is_executable returns True when no failed tasks"""
        self.assertTrue(self.plan.is_executable())
    
    def test_is_executable_with_failed_tasks(self):
        """Test is_executable returns False when there are failed tasks"""
        failed_task = RefactoringTask(
            id="task4",
            description="Failed task",
            file_path="file4.py",
            operation="migrate",
            status=TaskStatus.FAILED,
            error="Error"
        )
        
        plan_with_failed = RefactoringPlan(
            id="plan-failed",
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
        self.assertIsNotNone(updated_plan.started_at)
    
    def test_mark_task_in_progress_nonexistent_task(self):
        """Test marking non-existent task as in progress"""
        updated_plan = self.plan.mark_task_in_progress("nonexistent")
        
        # Should not change anything
        self.assertEqual(len(updated_plan.tasks), len(self.plan.tasks))
    
    def test_mark_task_completed(self):
        """Test marking a task as completed"""
        updated_plan = self.plan.mark_task_in_progress("task1")
        updated_plan = updated_plan.mark_task_completed("task1")
        
        task1 = next(t for t in updated_plan.tasks if t.id == "task1")
        self.assertEqual(task1.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task1.completed_at)
    
    def test_mark_task_completed_sets_plan_completed_at(self):
        """Test that marking last task completed sets plan completed_at"""
        # Mark all tasks except one as completed
        updated_plan = self.plan.mark_task_completed("task2")
        
        # Mark the last pending task
        updated_plan = updated_plan.mark_task_in_progress("task1")
        updated_plan = updated_plan.mark_task_completed("task1")
        
        # Mark the in-progress task
        updated_plan = updated_plan.mark_task_completed("task3")
        
        # Plan should have completed_at set
        self.assertIsNotNone(updated_plan.completed_at)
    
    def test_mark_task_failed(self):
        """Test marking a task as failed"""
        updated_plan = self.plan.mark_task_failed("task1", "Test error")
        
        task1 = next(t for t in updated_plan.tasks if t.id == "task1")
        self.assertEqual(task1.status, TaskStatus.FAILED)
        self.assertEqual(task1.error, "Test error")
    
    def test_plan_immutability(self):
        """Test that RefactoringPlan is immutable"""
        with self.assertRaises(Exception):
            self.plan.id = "new-id"
        
        with self.assertRaises(Exception):
            self.plan.tasks = []
    
    def test_plan_with_empty_tasks(self):
        """Test plan creation with empty tasks list"""
        plan = RefactoringPlan(
            id="plan-empty",
            codebase_id="codebase-test",
            tasks=[],
            created_at=datetime.now()
        )
        
        self.assertEqual(len(plan.tasks), 0)
        self.assertEqual(len(plan.get_pending_tasks()), 0)
        self.assertTrue(plan.is_executable())


class TestRefactoringDomainServiceComprehensive(unittest.TestCase):
    """Comprehensive test cases for RefactoringDomainService"""
    
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
    
    def test_create_refactoring_plan_success(self):
        """Test creating a refactoring plan successfully"""
        self.code_analyzer.identify_aws_s3_usage.return_value = ["s3_file.py"]
        
        plan = self.service.create_refactoring_plan(self.codebase)
        
        self.assertEqual(plan.codebase_id, "test-id")
        self.assertTrue(len(plan.tasks) > 0)
        self.code_analyzer.identify_aws_s3_usage.assert_called_once_with(self.codebase)
    
    def test_create_refactoring_plan_with_no_s3_files(self):
        """Test creating plan when no S3 files found"""
        self.code_analyzer.identify_aws_s3_usage.return_value = []
        
        plan = self.service.create_refactoring_plan(self.codebase)
        
        self.assertEqual(plan.codebase_id, "test-id")
        # Plan should still be created, possibly with no-op tasks
    
    def test_create_refactoring_plan_validates_codebase(self):
        """Test that plan creation validates codebase"""
        # Service should handle None codebase gracefully
        with self.assertRaises(Exception):
            self.service.create_refactoring_plan(None)


if __name__ == '__main__':
    unittest.main()
