"""
Test for Fargate to Cloud Run functionality
"""

import unittest
from unittest.mock import Mock
from infrastructure.adapters.extended_semantic_engine import ExtendedSemanticRefactoringService, ExtendedASTTransformationEngine
from infrastructure.adapters.service_mapping import ServiceMapper
from domain.value_objects import AWSService, GCPService


class TestFargateFunctionality(unittest.TestCase):
    """Test cases for AWS Fargate to Cloud Run migration"""
    
    def setUp(self):
        self.ast_engine = ExtendedASTTransformationEngine()
        self.service = ExtendedSemanticRefactoringService(self.ast_engine)
    
    def test_fargate_mapping_exists(self):
        """Test that Fargate to Cloud Run mapping exists"""
        mapper = ServiceMapper()
        mapping = mapper.get_mapping(AWSService.FARGATE)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.CLOUD_RUN)
        self.assertEqual(mapping.aws_service, AWSService.FARGATE)
        self.assertIn('ecs', str(mapping.aws_api_patterns))
    
    def test_fargate_to_cloudrun_transformation(self):
        """Test transforming Fargate (ECS) code to Cloud Run code"""
        original_code = """
import boto3
ecs_client = boto3.client('ecs')
response = ecs_client.run_task(
    cluster='my-cluster',
    taskDefinition='my-task-def',
    count=1
)
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "fargate_to_cloudrun"
        )
        
        # The refactored code should contain Cloud Run patterns
        self.assertIn("google.cloud", refactored_code)
        self.assertIn("run_v2", refactored_code)
        self.assertNotIn("boto3.client('ecs')", refactored_code)
    
    def test_auto_detect_fargate_and_transform_to_cloudrun(self):
        """Test auto-detecting Fargate and migrating to Cloud Run"""
        code_with_fargate = """
import boto3
# Fargate usage via ECS
ecs_client = boto3.client('ecs')
task_response = ecs_client.register_task_definition(
    family='my-task-family',
    containerDefinitions=[{
        'name': 'my-container',
        'image': 'my-image'
    }]
)
"""
        
        results = self.service.identify_and_migrate_services(code_with_fargate, "python")
        
        # Should have results from the analysis
        self.assertIsNotNone(results)


if __name__ == '__main__':
    unittest.main()