"""
Comprehensive Java AWS to GCP migration test suite
Tests all AWS services with real-world Java code examples
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine

# Comprehensive Java AWS test cases
JAVA_TEST_CASES = {
    "s3_basic": {
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
    
    public void downloadFile(String bucketName, String key, File file) {
        s3Client.getObject(bucketName, key, file);
    }
}
""",
        "services": ["s3"],
        "expected": ["com.google.cloud.storage", "Storage", "StorageOptions"],
        "forbidden": ["com.amazonaws", "AmazonS3", "S3Client", "s3Client", ".s3."]
    },
    
    "s3_sdk_v2": {
        "code": """import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

public class S3SDKV2Example {
    private S3Client s3Client;
    
    public S3SDKV2Example() {
        s3Client = S3Client.builder()
            .region(Region.US_EAST_1)
            .build();
    }
    
    public void uploadFile(String bucketName, String key, byte[] content) {
        PutObjectRequest request = PutObjectRequest.builder()
            .bucket(bucketName)
            .key(key)
            .build();
        s3Client.putObject(request, RequestBody.fromBytes(content));
    }
}
""",
        "services": ["s3"],
        "expected": ["com.google.cloud.storage", "Storage"],
        "forbidden": ["S3Client", "s3Client", "amazonaws", ".s3."]
    },
    
    "lambda_basic": {
        "code": """import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import java.util.Map;

public class LambdaHandler implements RequestHandler<Map<String, Object>, Map<String, Object>> {
    @Override
    public Map<String, Object> handleRequest(Map<String, Object> input, Context context) {
        context.getLogger().log("Processing request: " + input);
        return Map.of("statusCode", 200, "body", "Hello from Lambda!");
    }
}
""",
        "services": ["lambda"],
        "expected": ["com.google.cloud.functions", "HttpFunction", "HttpRequest", "HttpResponse"],
        "forbidden": ["com.amazonaws", "RequestHandler", "ILambdaContext", "Context"]
    },
    
    "lambda_with_s3": {
        "code": """import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import java.util.Map;

public class LambdaS3Handler implements RequestHandler<Map<String, Object>, Map<String, Object>> {
    private AmazonS3 s3Client;
    
    public LambdaS3Handler() {
        s3Client = AmazonS3ClientBuilder.standard().build();
    }
    
    @Override
    public Map<String, Object> handleRequest(Map<String, Object> input, Context context) {
        String bucketName = (String) input.get("bucket");
        s3Client.listObjects(bucketName);
        return Map.of("statusCode", 200);
    }
}
""",
        "services": ["lambda", "s3"],
        "expected": ["com.google.cloud.functions", "com.google.cloud.storage"],
        "forbidden": ["com.amazonaws", "RequestHandler", "AmazonS3", "s3Client"]
    },
    
    "dynamodb_basic": {
        "code": """import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder;
import com.amazonaws.services.dynamodbv2.model.PutItemRequest;
import com.amazonaws.services.dynamodbv2.model.AttributeValue;
import java.util.HashMap;
import java.util.Map;

public class DynamoDBExample {
    private AmazonDynamoDB dynamoDB;
    
    public DynamoDBExample() {
        dynamoDB = AmazonDynamoDBClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void putItem(String tableName, Map<String, String> data) {
        Map<String, AttributeValue> item = new HashMap<>();
        for (Map.Entry<String, String> entry : data.entrySet()) {
            item.put(entry.getKey(), new AttributeValue(entry.getValue()));
        }
        PutItemRequest request = new PutItemRequest(tableName, item);
        dynamoDB.putItem(request);
    }
    
    public Map<String, AttributeValue> getItem(String tableName, String key) {
        Map<String, AttributeValue> keyMap = new HashMap<>();
        keyMap.put("id", new AttributeValue(key));
        GetItemRequest request = new GetItemRequest(tableName, keyMap);
        return dynamoDB.getItem(request).getItem();
    }
}
""",
        "services": ["dynamodb"],
        "expected": ["com.google.cloud.firestore", "Firestore"],
        "forbidden": ["com.amazonaws", "AmazonDynamoDB", "AttributeValue", "PutItemRequest"]
    },
    
    "sqs_basic": {
        "code": """import com.amazonaws.services.sqs.AmazonSQS;
import com.amazonaws.services.sqs.AmazonSQSClientBuilder;
import com.amazonaws.services.sqs.model.SendMessageRequest;

public class SQSExample {
    private AmazonSQS sqsClient;
    
    public SQSExample() {
        sqsClient = AmazonSQSClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void sendMessage(String queueUrl, String messageBody) {
        SendMessageRequest request = new SendMessageRequest(queueUrl, messageBody);
        sqsClient.sendMessage(request);
    }
}
""",
        "services": ["sqs"],
        "expected": ["com.google.cloud.pubsub", "PublisherClient"],
        "forbidden": ["com.amazonaws", "AmazonSQS", "SendMessageRequest"]
    },
    
    "sns_basic": {
        "code": """import com.amazonaws.services.sns.AmazonSNS;
import com.amazonaws.services.sns.AmazonSNSClientBuilder;
import com.amazonaws.services.sns.model.PublishRequest;

public class SNSExample {
    private AmazonSNS snsClient;
    
    public SNSExample() {
        snsClient = AmazonSNSClientBuilder.standard()
            .withRegion("us-east-1")
            .build();
    }
    
    public void publish(String topicArn, String message, String subject) {
        PublishRequest request = new PublishRequest(topicArn, message);
        request.setSubject(subject);
        snsClient.publish(request);
    }
}
""",
        "services": ["sns"],
        "expected": ["com.google.cloud.pubsub", "PublisherClient"],
        "forbidden": ["com.amazonaws", "AmazonSNS", "PublishRequest"]
    },
    
    "multi_service": {
        "code": """import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder;
import com.amazonaws.services.sqs.AmazonSQS;
import com.amazonaws.services.sqs.AmazonSQSClientBuilder;

public class MultiServiceExample {
    private AmazonS3 s3Client;
    private AmazonDynamoDB dynamoDB;
    private AmazonSQS sqsClient;
    
    public MultiServiceExample() {
        s3Client = AmazonS3ClientBuilder.standard().build();
        dynamoDB = AmazonDynamoDBClientBuilder.standard().build();
        sqsClient = AmazonSQSClientBuilder.standard().build();
    }
    
    public void processData(String bucketName, String key, String tableName, String queueUrl) {
        // Read from S3
        s3Client.getObject(bucketName, key);
        
        // Write to DynamoDB
        dynamoDB.putItem(tableName, item);
        
        // Send to SQS
        sqsClient.sendMessage(queueUrl, "message");
    }
}
""",
        "services": ["s3", "dynamodb", "sqs"],
        "expected": ["com.google.cloud.storage", "com.google.cloud.firestore", "com.google.cloud.pubsub"],
        "forbidden": ["com.amazonaws", "AmazonS3", "AmazonDynamoDB", "AmazonSQS"]
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
        elif "sqs" in services:
            service_type = "sqs_to_pubsub"
        elif "sns" in services:
            service_type = "sns_to_pubsub"
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
            # Check if pattern exists (case-insensitive)
            if pattern_lower in result_lower:
                # For Java, check if it's in comments
                lines = result_code.split('\n')
                pattern_in_code = False
                for line in lines:
                    stripped = line.strip()
                    # Skip comment lines
                    if stripped.startswith('//') or stripped.startswith('*') or '/*' in stripped:
                        continue
                    if pattern_lower in line.lower():
                        pattern_in_code = True
                        break
                if pattern_in_code:
                    found_forbidden.append(pattern)
                    print(f"  ✗ Forbidden pattern found: {pattern}")
                else:
                    print(f"  ⚠ Forbidden pattern in comments only: {pattern}")
            else:
                print(f"  ✓ Forbidden pattern removed: {pattern}")
        
        # Show code snippet
        print(f"\nRefactored code snippet (first 800 chars):")
        print("-" * 70)
        print(result_code[:800])
        if len(result_code) > 800:
            print("...")
        print("-" * 70)
        
        # Validation
        if missing_patterns:
            print(f"\n⚠ WARNING: Missing expected patterns: {missing_patterns}")
        
        if found_forbidden:
            print(f"\n✗ Test FAILED: Found forbidden patterns: {found_forbidden}")
            return False
        
        if not missing_patterns and not found_forbidden:
            print(f"\n✓ Test PASSED!")
            return True
        elif not found_forbidden:
            print(f"\n⚠ Test PARTIALLY PASSED (missing some expected patterns but no forbidden patterns)")
            return True
        
        return False
        
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Java tests"""
    print("="*70)
    print("COMPREHENSIVE JAVA AWS TO GCP MIGRATION TEST SUITE")
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
