"""
Test Java migration functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine

# Java test cases
JAVA_TEST_CASES = {
    "s3_java": {
        "code": """import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import com.amazonaws.services.s3.model.PutObjectRequest;
import java.io.File;

public class S3Example {
    private AmazonS3 s3Client;
    
    public S3Example() {
        s3Client = AmazonS3ClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void uploadFile(String bucketName, String key, File file) {
        PutObjectRequest request = new PutObjectRequest(bucketName, key, file);
        s3Client.putObject(request);
    }
}
""",
        "services": ["s3"],
        "expected": ["com.google.cloud.storage", "Storage"],
        "forbidden": ["com.amazonaws", "AmazonS3"]
    },
    
    "lambda_java": {
        "code": """import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import java.util.Map;

public class LambdaHandler implements RequestHandler<Map<String, Object>, Map<String, Object>> {
    @Override
    public Map<String, Object> handleRequest(Map<String, Object> input, Context context) {
        return Map.of("statusCode", 200, "body", "Hello from Lambda!");
    }
}
""",
        "services": ["lambda"],
        "expected": ["com.google.cloud.functions", "HttpFunction"],
        "forbidden": ["com.amazonaws", "RequestHandler"]
    },
    
    "dynamodb_java": {
        "code": """import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder;
import com.amazonaws.services.dynamodbv2.model.PutItemRequest;
import java.util.HashMap;
import java.util.Map;

public class DynamoDBExample {
    private AmazonDynamoDB dynamoDB;
    
    public DynamoDBExample() {
        dynamoDB = AmazonDynamoDBClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void putItem(String tableName, Map<String, Object> item) {
        PutItemRequest request = new PutItemRequest()
            .withTableName(tableName)
            .withItem(convertToAttributeValues(item));
        dynamoDB.putItem(request);
    }
    
    private Map<String, com.amazonaws.services.dynamodbv2.model.AttributeValue> convertToAttributeValues(Map<String, Object> item) {
        return new HashMap<>();
    }
}
""",
        "services": ["dynamodb"],
        "expected": ["com.google.cloud.firestore", "Firestore"],
        "forbidden": ["com.amazonaws", "AmazonDynamoDB"]
    }
}


def test_java_migration(test_name: str, test_case: dict):
    """Test Java migration"""
    print(f"\n{'='*70}")
    print(f"Testing: {test_name}")
    print(f"{'='*70}")
    
    code = test_case["code"]
    services = test_case["services"]
    expected = test_case.get("expected", [])
    forbidden = test_case.get("forbidden", [])
    
    print(f"Services: {services}")
    print(f"Expected patterns: {expected}")
    print(f"Forbidden patterns: {forbidden}")
    
    try:
        engine = ExtendedASTTransformationEngine()
        
        # Determine service type
        if "dynamodb" in services:
            service_type = "dynamodb_to_firestore"
        elif "s3" in services:
            service_type = "s3_to_gcs"
        elif "lambda" in services:
            service_type = "lambda_to_cloud_functions"
        else:
            service_type = "multi_service"
        
        print(f"\nService type: {service_type}")
        print(f"Language: java")
        
        # Migrate
        result_code, variable_mapping = engine.transform_code(code, "java", {
            "operation": "service_migration",
            "service_type": service_type,
            "services": services
        })
        
        print(f"\nOriginal code length: {len(code)}")
        print(f"Refactored code length: {len(result_code)}")
        
        # Check results
        result_lower = result_code.lower()
        
        print(f"\nResults:")
        missing_patterns = []
        for pattern in expected:
            pattern_lower = pattern.lower()
            if pattern_lower not in result_lower:
                missing_patterns.append(pattern)
                print(f"  ✗ Missing: {pattern}")
            else:
                print(f"  ✓ Found: {pattern}")
        
        found_forbidden = []
        for pattern in forbidden:
            pattern_lower = pattern.lower()
            if pattern_lower in result_lower:
                found_forbidden.append(pattern)
                print(f"  ✗ Forbidden pattern found: {pattern}")
            else:
                print(f"  ✓ Forbidden pattern removed: {pattern}")
        
        # Show code snippet
        print(f"\nRefactored code snippet (first 500 chars):")
        print("-" * 70)
        print(result_code[:500])
        if len(result_code) > 500:
            print("...")
        print("-" * 70)
        
        # Validation
        if missing_patterns:
            print(f"\n✗ Test FAILED: Missing expected patterns: {missing_patterns}")
            return False
        
        if found_forbidden:
            print(f"\n✗ Test FAILED: Found forbidden patterns: {found_forbidden}")
            return False
        
        print(f"\n✓ Test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Java tests"""
    print("="*70)
    print("JAVA MIGRATION TEST SUITE")
    print("="*70)
    
    results = []
    for test_name, test_case in JAVA_TEST_CASES.items():
        success = test_java_migration(test_name, test_case)
        results.append({
            "test_name": test_name,
            "success": success
        })
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["success"]:
                print(f"  ✗ {r['test_name']}")
    
    return all(r["success"] for r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
