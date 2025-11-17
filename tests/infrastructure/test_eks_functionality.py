"""
Test for EKS to GKE functionality
"""

import unittest
from unittest.mock import Mock
from infrastructure.adapters.extended_semantic_engine import ExtendedSemanticRefactoringService, ExtendedASTTransformationEngine
from infrastructure.adapters.service_mapping import ServiceMapper
from domain.value_objects import AWSService, GCPService


class TestEKSFunctionality(unittest.TestCase):
    """Test cases for AWS EKS to GKE migration"""
    
    def setUp(self):
        self.ast_engine = ExtendedASTTransformationEngine()
        self.service = ExtendedSemanticRefactoringService(self.ast_engine)
    
    def test_eks_mapping_exists(self):
        """Test that EKS to GKE mapping exists"""
        mapper = ServiceMapper()
        mapping = mapper.get_mapping(AWSService.EKS)
        
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.gcp_service, GCPService.GKE)
        self.assertEqual(mapping.aws_service, AWSService.EKS)
        self.assertIn('eks', str(mapping.aws_api_patterns))
    
    def test_eks_to_gke_transformation(self):
        """Test transforming EKS code to GKE code"""
        original_code = """
import boto3
eks_client = boto3.client('eks')
cluster_response = eks_client.create_cluster(
    name='test-cluster',
    roleArn='arn:aws:iam::123456789012:role/eks-service-role',
    resourcesVpcConfig={'subnetIds': ['subnet-12345']}
)
"""
        
        refactored_code = self.service.apply_refactoring(
            original_code, 
            "python", 
            "eks_to_gke"
        )
        
        # The refactored code should contain GKE patterns
        self.assertIn("google.cloud", refactored_code)
        self.assertIn("container_v1", refactored_code)
        self.assertNotIn("boto3.client('eks')", refactored_code)
    
    def test_auto_detect_eks_and_transform_to_gke(self):
        """Test auto-detecting EKS and migrating to GKE"""
        code_with_eks = """
import boto3
# EKS usage
eks_client = boto3.client('eks')
cluster_response = eks_client.describe_cluster(name='my-cluster')
"""
        
        results = self.service.identify_and_migrate_services(code_with_eks, "python")
        
        # Should have results from the analysis
        self.assertIsNotNone(results)


if __name__ == '__main__':
    unittest.main()