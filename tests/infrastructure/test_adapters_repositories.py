"""
Infrastructure Layer Tests

Testing the infrastructure adapters and repositories
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch
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


class TestFileRepositoryAdapter(unittest.TestCase):
    """Test cases for FileRepositoryAdapter"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = FileRepositoryAdapter(base_path=self.temp_dir)
    
    def test_create_backup(self):
        """Test creating a backup of a file"""
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Create backup
        backup_path = self.adapter.create_backup(test_file)
        
        # Verify backup exists and has same content
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "test content")


class TestCodebaseRepositoryAdapter(unittest.TestCase):
    """Test cases for CodebaseRepositoryAdapter"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = CodebaseRepositoryAdapter(storage_path=self.temp_dir)
    
    def test_save_and_load(self):
        """Test saving and loading a codebase"""
        codebase = Codebase(
            id="test-id",
            path="/path",
            language=ProgrammingLanguage.PYTHON,
            files=["file1.py"],
            dependencies={"boto3": "1.26.0"},
            created_at=datetime.now()
        )
        
        # Save the codebase
        self.adapter.save(codebase)
        
        # Load the codebase
        loaded = self.adapter.load("test-id")
        
        # Verify the loaded codebase matches
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, "test-id")
        self.assertEqual(loaded.language, ProgrammingLanguage.PYTHON)
        self.assertEqual(loaded.files, ["file1.py"])


class TestPlanRepositoryAdapter(unittest.TestCase):
    """Test cases for PlanRepositoryAdapter"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = PlanRepositoryAdapter(storage_path=self.temp_dir)
    
    def test_save_and_load(self):
        """Test saving and loading a refactoring plan"""
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
        
        # Save the plan
        self.adapter.save(plan)
        
        # Load the plan
        loaded = self.adapter.load("plan-test")
        
        # Verify the loaded plan matches
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, "plan-test")
        self.assertEqual(loaded.codebase_id, "test-id")
        self.assertEqual(len(loaded.tasks), 1)
        self.assertEqual(loaded.tasks[0].id, "task1")


class TestCodeAnalyzerAdapter(unittest.TestCase):
    """Test cases for CodeAnalyzerAdapter"""
    
    def setUp(self):
        self.adapter = CodeAnalyzerAdapter()
    
    def test_identify_aws_s3_usage_python(self):
        """Test identifying AWS S3 usage in Python files"""
        # Create a temporary Python file with S3 usage
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import boto3
s3_client = boto3.client('s3')
s3_client.upload_file('local_file', 'bucket_name', 's3_key')
""")
            temp_file = f.name
        
        try:
            # Create a mock codebase
            codebase = Codebase(
                id="test-id",
                path="/path",
                language=ProgrammingLanguage.PYTHON,
                files=[temp_file],
                dependencies={},
                created_at=datetime.now()
            )
            
            # Identify S3 usage
            s3_files = self.adapter.identify_aws_s3_usage(codebase)
            
            # Should find the file with S3 usage
            self.assertIn(temp_file, s3_files)
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_analyze_dependencies_python(self):
        """Test analyzing Python dependencies"""
        # Create a temporary requirements.txt file
        with tempfile.NamedTemporaryFile(mode='w', suffix='requirements.txt', delete=False) as f:
            f.write("boto3==1.26.0\nrequests==2.28.0\n")
            temp_file = f.name
        
        try:
            # Create a mock codebase
            codebase = Codebase(
                id="test-id",
                path="/path",
                language=ProgrammingLanguage.PYTHON,
                files=[temp_file],
                dependencies={},
                created_at=datetime.now()
            )
            
            # Analyze dependencies
            deps = self.adapter.analyze_dependencies(codebase)
            
            # Should find boto3 dependency
            self.assertIn("boto3", deps)
        finally:
            # Clean up
            os.unlink(temp_file)


class TestLLMProviderAdapter(unittest.TestCase):
    """Test cases for LLMProviderAdapter"""
    
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
    
    def test_generate_refactoring_intent(self):
        """Test generating refactoring intent"""
        intent = self.adapter.generate_refactoring_intent(
            self.codebase, "test.py", "gcs"
        )
        
        # Should return a non-empty string
        self.assertIsInstance(intent, str)
        self.assertGreater(len(intent), 0)
    
    def test_generate_recipe(self):
        """Test generating recipe"""
        analysis = {
            "file_path": "test.py",
            "intent": "migrate to gcs",
            "target": "gcs"
        }
        
        recipe = self.adapter.generate_recipe(analysis)
        
        # Should return a non-empty string
        self.assertIsInstance(recipe, str)
        self.assertGreater(len(recipe), 0)


class TestASTTransformationAdapter(unittest.TestCase):
    """Test cases for ASTTransformationAdapter"""
    
    def setUp(self):
        self.adapter = ASTTransformationAdapter()
    
    def test_apply_recipe(self):
        """Test applying a recipe to transform code"""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import boto3
s3_client = boto3.client('s3')
s3_client.upload_file('local_file', 'bucket_name', 's3_key')
""")
            temp_file = f.name
        
        try:
            # Apply transformation (this will use regex fallback)
            recipe = "s3_to_gcs"
            result = self.adapter.apply_recipe(recipe, temp_file)
            
            # Result should contain the transformation comment
            self.assertIn("TRANSFORMED BY CLOUD REFACTOR AGENT", result)
        finally:
            # Clean up
            os.unlink(temp_file)


class TestTestRunnerAdapter(unittest.TestCase):
    """Test cases for TestRunnerAdapter"""
    
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
    
    def test_run_tests(self):
        """Test running tests"""
        results = self.adapter.run_tests(self.codebase)
        
        # Should return expected structure
        self.assertIn("success", results)
        self.assertIn("total_tests", results)
        self.assertIn("passed", results)
        self.assertTrue(results["success"])


if __name__ == '__main__':
    unittest.main()