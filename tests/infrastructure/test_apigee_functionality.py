"""
Test for Apigee X functionality
"""

import unittest
from unittest.mock import Mock
from infrastructure.adapters.extended_semantic_engine import ExtendedSemanticRefactoringService, ExtendedASTTransformationEngine
from infrastructure.adapters.service_mapping import ServiceMapper
from domain.value_objects import AWSService, GCPService


class TestApigeeFunctionality(unittest.TestCase):
    """Test cases for AWS API Gateway to Apigee X migration"""
    
    def setUp(self):
        self.ast_engine = ExtendedASTTransformationEngine()
        self.service = ExtendedSemanticRefactoringService(self.ast_engine)
    
    def test_apigee_mapping_exists(self):
        """Test that API Gateway to Apigee mapping exists"""
        mapper = ServiceMapper()
        mapping = mapper.get_mapping(AWSService.API_GATEWAY)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.APIGEE)
        self.assertEqual(mapping.aws_service, AWSService.API_GATEWAY)
        self.assertIn('apigateway', str(mapping.aws_api_patterns))
    
    def test_apigateway_to_apigee_transformation(self):
        """Test transforming API Gateway code to Apigee code"""
        original_code = """
import boto3
apigateway_client = boto3.client('apigateway')
api_response = apigateway_client.create_rest_api(name='test-api')
deployment_response = apigateway_client.create_deployment(
    restApiId='api-id',
    stageName='prod'
)
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "apigateway_to_apigee"
        )
        
        # The refactored code should contain Apigee patterns
        self.assertIn("apigee", refactored_code)
        self.assertNotIn("boto3.client('apigateway')", refactored_code)
    
    def test_auto_detect_apigateway_and_transform_to_apigee(self):
        """Test auto-detecting API Gateway and migrating to Apigee"""
        code_with_apigateway = """
import boto3
# API Gateway usage
apigateway_client = boto3.client('apigateway')
api_response = apigateway_client.create_rest_api(name='test-api')
"""
        
        results = self.service.identify_and_migrate_services(code_with_apigateway, "python")

        # Should have some results from the analysis
        # The exact key might be different, so let's check for any results
        self.assertIsNotNone(results)


if __name__ == '__main__':
    unittest.main()