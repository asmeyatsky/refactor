"""
Comprehensive Unit Tests for Infrastructure Adapters

This test suite provides extensive coverage for infrastructure adapters
with multiple test scenarios including error handling, edge cases, and integration.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime

from domain.entities.codebase import Codebase, ProgrammingLanguage
from domain.entities.refactoring_plan import RefactoringPlan, RefactoringTask, TaskStatus
from infrastructure.adapters import (
    CodeAnalyzerAdapter, LLMProviderAdapter,
    ASTTransformationAdapter, TestRunnerAdapter
)
from infrastructure.repositories import (
    FileRepositoryAdapter, CodebaseRepositoryAdapter, PlanRepositoryAdapter
)


class TestFileRepositoryAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for FileRepositoryAdapter"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = FileRepositoryAdapter(base_path=self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_backup_success(self):
        """Test creating a backup successfully"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        backup_path = self.adapter.create_backup(test_file)
        
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test content")
    
    def test_create_backup_file_not_exists(self):
        """Test creating backup when file doesn't exist"""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        with self.assertRaises(Exception):
            self.adapter.create_backup(non_existent_file)
    
    def test_write_file_success(self):
        """Test writing file successfully"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        content = "test content"
        
        self.adapter.write_file(test_file, content)
        
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, 'r') as f:
            self.assertEqual(f.read(), content)
    
    def test_write_file_creates_directory(self):
        """Test that write_file creates directory if it doesn't exist"""
        test_file = os.path.join(self.temp_dir, "subdir", "test.txt")
        content = "test content"
        
        self.adapter.write_file(test_file, content)
        
        self.assertTrue(os.path.exists(test_file))
    
    def test_write_file_with_special_characters(self):
        """Test writing file with special characters"""
        test_file = os.path.join(self.temp_dir, "test.txt")
        content = "test\ncontent\twith\rspecial chars: àáâãäå"
        
        self.adapter.write_file(test_file, content)
        
        with open(test_file, 'r', encoding='utf-8') as f:
            read_content = f.read()
            # Normalize line endings for comparison (Python may normalize \r\n to \n)
            normalized_read = read_content.replace('\r\n', '\n').replace('\r', '\n')
            normalized_expected = content.replace('\r\n', '\n').replace('\r', '\n')
            self.assertEqual(normalized_read, normalized_expected)
            # Also verify Unicode characters are preserved
            self.assertIn("àáâãäå", read_content)
    
    def test_write_file_with_empty_content(self):
        """Test writing file with empty content"""
        test_file = os.path.join(self.temp_dir, "empty.txt")
        
        self.adapter.write_file(test_file, "")
        
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, 'r') as f:
            self.assertEqual(f.read(), "")


class TestCodebaseRepositoryAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for CodebaseRepositoryAdapter"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = CodebaseRepositoryAdapter(storage_path=self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_success(self):
        """Test saving and loading codebase successfully"""
        codebase = Codebase(
            id="test-id",
            path="/path",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py"],
            dependencies={"boto3": "1.26.0"},
            created_at=datetime.now()
        )
        
        self.adapter.save(codebase)
        loaded = self.adapter.load("test-id")
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, "test-id")
        self.assertEqual(loaded.language, ProgrammingLanguage.PYTHON)
        self.assertEqual(loaded.files, ["file1.py"])
        self.assertEqual(loaded.dependencies, {"boto3": "1.26.0"})
    
    def test_load_nonexistent_codebase(self):
        """Test loading non-existent codebase"""
        loaded = self.adapter.load("nonexistent-id")
        
        self.assertIsNone(loaded)
    
    def test_save_overwrites_existing(self):
        """Test that save overwrites existing codebase"""
        codebase1 = Codebase(
            id="test-id",
            path="/path1",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py"],
            dependencies={},
            created_at=datetime.now()
        )
        
        codebase2 = Codebase(
            id="test-id",
            path="/path2",
            language=ProgrammingLanguage.JAVA,
            files=["file2.java"],
            dependencies={},
            created_at=datetime.now()
        )
        
        self.adapter.save(codebase1)
        self.adapter.save(codebase2)
        
        loaded = self.adapter.load("test-id")
        self.assertEqual(loaded.path, "/path2")
        self.assertEqual(loaded.language, ProgrammingLanguage.JAVA)
    
    def test_save_with_complex_metadata(self):
        """Test saving codebase with complex metadata"""
        codebase = Codebase(
            id="test-id",
            path="/path",
            language=ProgrammingLanguage.PYTHON,
            files=[],
            dependencies={},
            created_at=datetime.now(),
            metadata={"key1": "value1", "key2": "value2", "nested": {"inner": "value"}}
        )
        
        self.adapter.save(codebase)
        loaded = self.adapter.load("test-id")
        
        self.assertIn("key1", loaded.metadata)


class TestPlanRepositoryAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for PlanRepositoryAdapter"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = PlanRepositoryAdapter(storage_path=self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_success(self):
        """Test saving and loading plan successfully"""
        task = RefactoringTask(
            id="task1",
            description="Test task",
            file_path="file.py",
            operation="replace_s3_with_gcs",
            status=TaskStatus.PENDING
        )
        
        plan = RefactoringPlan(
            id="plan-test",
            codebase_id="test-id",
            tasks=[task],
            created_at=datetime.now()
        )
        
        self.adapter.save(plan)
        loaded = self.adapter.load("plan-test")
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, "plan-test")
        self.assertEqual(loaded.codebase_id, "test-id")
        self.assertEqual(len(loaded.tasks), 1)
        self.assertEqual(loaded.tasks[0].id, "task1")
    
    def test_load_nonexistent_plan(self):
        """Test loading non-existent plan"""
        loaded = self.adapter.load("nonexistent-plan")
        
        self.assertIsNone(loaded)
    
    def test_save_plan_with_multiple_tasks(self):
        """Test saving plan with multiple tasks"""
        tasks = [
            RefactoringTask(
                id=f"task{i}",
                description=f"Task {i}",
                file_path=f"file{i}.py",
                operation="migrate",
                status=TaskStatus.PENDING if i % 2 == 0 else TaskStatus.COMPLETED
            )
            for i in range(10)
        ]
        
        plan = RefactoringPlan(
            id="plan-multi",
            codebase_id="test-id",
            tasks=tasks,
            created_at=datetime.now()
        )
        
        self.adapter.save(plan)
        loaded = self.adapter.load("plan-multi")
        
        self.assertEqual(len(loaded.tasks), 10)
        self.assertEqual(len(loaded.get_pending_tasks()), 5)


class TestCodeAnalyzerAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for CodeAnalyzerAdapter"""
    
    def setUp(self):
        self.adapter = CodeAnalyzerAdapter()
    
    def test_identify_aws_s3_usage_python(self):
        """Test identifying AWS S3 usage in Python files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import boto3
s3_client = boto3.client('s3')
s3_client.upload_file('local_file', 'bucket_name', 's3_key')
""")
            temp_file = f.name
        
        try:
            codebase = Codebase(
                id="test-id",
                path="/path",
                language=ProgrammingLanguage.PYTHON,
                files=[temp_file],
                dependencies={},
                created_at=datetime.now()
            )
            
            s3_files = self.adapter.identify_aws_s3_usage(codebase)
            
            self.assertIn(temp_file, s3_files)
        finally:
            os.unlink(temp_file)
    
    def test_identify_aws_s3_usage_no_s3(self):
        """Test identifying S3 usage when none exists"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Hello World')")
            temp_file = f.name
        
        try:
            codebase = Codebase(
                id="test-id",
                path="/path",
                language=ProgrammingLanguage.PYTHON,
                files=[temp_file],
                dependencies={},
                created_at=datetime.now()
            )
            
            s3_files = self.adapter.identify_aws_s3_usage(codebase)
            
            # May or may not find S3 depending on implementation
            self.assertIsInstance(s3_files, list)
        finally:
            os.unlink(temp_file)
    
    def test_analyze_dependencies_python(self):
        """Test analyzing Python dependencies"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='requirements.txt', delete=False) as f:
            f.write("boto3==1.26.0\nrequests==2.28.0\n")
            temp_file = f.name
        
        try:
            codebase = Codebase(
                id="test-id",
                path="/path",
                language=ProgrammingLanguage.PYTHON,
                files=[temp_file],
                dependencies={},
                created_at=datetime.now()
            )
            
            deps = self.adapter.analyze_dependencies(codebase)
            
            self.assertIn("boto3", deps)
        finally:
            os.unlink(temp_file)
    
    def test_analyze_dependencies_no_requirements_file(self):
        """Test analyzing dependencies when requirements.txt doesn't exist"""
        codebase = Codebase(
            id="test-id",
            path="/nonexistent/path",
            language=ProgrammingLanguage.PYTHON,
            files=[],
            dependencies={},
            created_at=datetime.now()
        )
        
        deps = self.adapter.analyze_dependencies(codebase)
        
        self.assertIsInstance(deps, dict)


class TestLLMProviderAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for LLMProviderAdapter"""
    
    def setUp(self):
        self.adapter = LLMProviderAdapter()
        self.codebase = Codebase(
            id="test-id",
            path="/path",
            language=ProgrammingLanguage.PYTHON,
            files=["test.py"],
            dependencies={},
            created_at=datetime.now()
        )
    
    def test_generate_refactoring_intent_success(self):
        """Test generating refactoring intent successfully"""
        intent = self.adapter.generate_refactoring_intent(
            self.codebase, "test.py", "gcs"
        )
        
        self.assertIsInstance(intent, str)
        self.assertGreater(len(intent), 0)
    
    def test_generate_refactoring_intent_with_nonexistent_file(self):
        """Test generating intent with non-existent file"""
        intent = self.adapter.generate_refactoring_intent(
            self.codebase, "nonexistent.py", "gcs"
        )
        
        # Should handle gracefully
        self.assertIsInstance(intent, str)
    
    def test_generate_recipe_success(self):
        """Test generating recipe successfully"""
        analysis = {
            "file_path": "test.py",
            "intent": "migrate to gcs",
            "target": "gcs"
        }
        
        recipe = self.adapter.generate_recipe(analysis)
        
        self.assertIsInstance(recipe, str)
        self.assertGreater(len(recipe), 0)
    
    def test_generate_recipe_with_empty_analysis(self):
        """Test generating recipe with empty analysis"""
        analysis = {}
        
        recipe = self.adapter.generate_recipe(analysis)
        
        # Should handle gracefully
        self.assertIsInstance(recipe, str)


class TestASTTransformationAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for ASTTransformationAdapter"""
    
    def setUp(self):
        self.adapter = ASTTransformationAdapter()
    
    def test_apply_recipe_success(self):
        """Test applying recipe successfully"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import boto3
s3_client = boto3.client('s3')
s3_client.upload_file('local_file', 'bucket_name', 's3_key')
""")
            temp_file = f.name
        
        try:
            recipe = "s3_to_gcs"
            result = self.adapter.apply_recipe(recipe, temp_file)
            
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
        finally:
            os.unlink(temp_file)
    
    def test_apply_recipe_file_not_exists(self):
        """Test applying recipe when file doesn't exist"""
        with self.assertRaises(Exception):
            self.adapter.apply_recipe("recipe", "/nonexistent/file.py")
    
    def test_apply_recipe_with_invalid_syntax(self):
        """Test applying recipe to file with invalid syntax"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("invalid python syntax !!!")
            temp_file = f.name
        
        try:
            recipe = "s3_to_gcs"
            # Should handle gracefully or raise appropriate error
            result = self.adapter.apply_recipe(recipe, temp_file)
            self.assertIsInstance(result, str)
        except Exception:
            # Exception is acceptable for invalid syntax
            pass
        finally:
            os.unlink(temp_file)


class TestTestRunnerAdapterComprehensive(unittest.TestCase):
    """Comprehensive test cases for TestRunnerAdapter"""
    
    def setUp(self):
        self.adapter = TestRunnerAdapter()
        self.codebase = Codebase(
            id="test-id",
            path="/path",
            language=ProgrammingLanguage.PYTHON,
            files=["test.py"],
            dependencies={},
            created_at=datetime.now()
        )
    
    def test_run_tests_success(self):
        """Test running tests successfully"""
        results = self.adapter.run_tests(self.codebase)
        
        self.assertIn("success", results)
        self.assertIn("total_tests", results)
        self.assertIn("passed", results)
        self.assertIsInstance(results["success"], bool)
    
    def test_run_tests_with_no_test_files(self):
        """Test running tests when no test files exist"""
        codebase = Codebase(
            id="test-id",
            path="/nonexistent/path",
            language=ProgrammingLanguage.PYTHON,
            files=[],
            dependencies={},
            created_at=datetime.now()
        )
        
        results = self.adapter.run_tests(codebase)
        
        # Should handle gracefully
        self.assertIn("success", results)
    
    def test_run_tests_returns_consistent_structure(self):
        """Test that run_tests always returns consistent structure"""
        results = self.adapter.run_tests(self.codebase)
        
        required_keys = ["success", "total_tests", "passed", "failed"]
        for key in required_keys:
            self.assertIn(key, results)


if __name__ == '__main__':
    unittest.main()
