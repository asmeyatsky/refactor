"""Single Node.js test to see full output"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
from application.use_cases.validate_gcp_code_use_case import ValidateGCPCodeUseCase

code = """
const AWS = require('aws-sdk');

const s3 = new AWS.S3({
    region: 'us-east-1'
});

async function uploadFile(bucketName, key, filePath) {
    const params = {
        Bucket: bucketName,
        Key: key,
        Body: require('fs').readFileSync(filePath)
    };
    
    try {
        const result = await s3.putObject(params).promise();
        console.log('File uploaded successfully:', result.ETag);
        return result;
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}
"""

engine = ExtendedASTTransformationEngine()
transformation_recipe = {
    "operation": "service_migration",
    "service_type": "s3_to_gcs",
    "target_api": "GCP"
}

print("="*80)
print("TRANSFORMING...")
print("="*80)
transformed_code, _ = engine.transform_code(code, "javascript", transformation_recipe)

print("\n" + "="*80)
print("TRANSFORMED CODE:")
print("="*80)
print(transformed_code)

print("\n" + "="*80)
print("VALIDATING...")
print("="*80)
validator = ValidateGCPCodeUseCase()
result = validator.validate(transformed_code, language="javascript")

print(f"\nAWS Patterns: {result.aws_patterns_found}")
print(f"Syntax Valid: {result.syntax_valid}")
print(f"GCP API Correct: {result.gcp_api_correct}")
