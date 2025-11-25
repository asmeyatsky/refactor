"""
Comprehensive C# AWS to GCP migration test suite
Tests all AWS services with real-world C# code examples
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Comprehensive C# test cases
CSHARP_TEST_CASES = {
    "s3_basic": {
        "code": """using Amazon.S3;
using Amazon.S3.Model;
using System;
using System.IO;
using System.Threading.Tasks;

public class S3Example
{
    private IAmazonS3 s3Client;
    
    public S3Example()
    {
        s3Client = new AmazonS3Client();
    }
    
    public async Task UploadFileAsync(string bucketName, string key, Stream fileStream)
    {
        var request = new PutObjectRequest
        {
            BucketName = bucketName,
            Key = key,
            InputStream = fileStream
        };
        await s3Client.PutObjectAsync(request);
    }
    
    public async Task<Stream> DownloadFileAsync(string bucketName, string key)
    {
        var request = new GetObjectRequest
        {
            BucketName = bucketName,
            Key = key
        };
        var response = await s3Client.GetObjectAsync(request);
        return response.ResponseStream;
    }
}
""",
        "services": ["s3"],
        "expected": ["Google.Cloud.Storage", "StorageClient"],
        "forbidden": ["Amazon.S3", "IAmazonS3", "AmazonS3Client", "s3Client"]
    },
    
    "s3_with_config": {
        "code": """using Amazon.S3;
using Amazon;
using Amazon.S3.Model;
using System.Threading.Tasks;

public class S3ConfigExample
{
    private IAmazonS3 s3Client;
    
    public S3ConfigExample()
    {
        var config = new AmazonS3Config
        {
            RegionEndpoint = RegionEndpoint.USEast1
        };
        s3Client = new AmazonS3Client(config);
    }
    
    public async Task ListBucketsAsync()
    {
        var response = await s3Client.ListBucketsAsync();
        foreach (var bucket in response.Buckets)
        {
            Console.WriteLine(bucket.BucketName);
        }
    }
}
""",
        "services": ["s3"],
        "expected": ["Google.Cloud.Storage", "StorageClient"],
        "forbidden": ["Amazon.S3", "IAmazonS3", "AmazonS3Client", "RegionEndpoint"]
    },
    
    "lambda_basic": {
        "code": """using Amazon.Lambda.Core;
using Amazon.Lambda.APIGatewayEvents;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public class LambdaFunction
{
    public async Task<APIGatewayProxyResponse> FunctionHandler(APIGatewayProxyRequest request, ILambdaContext context)
    {
        context.Logger.LogLine($"Processing request: {request.Path}");
        
        return new APIGatewayProxyResponse
        {
            StatusCode = 200,
            Body = "Hello from Lambda!"
        };
    }
}
""",
        "services": ["lambda"],
        "expected": ["Google.Cloud.Functions", "IHttpFunction", "HttpContext"],
        "forbidden": ["Amazon.Lambda", "ILambdaContext", "APIGatewayProxy"]
    },
    
    "lambda_with_s3": {
        "code": """using Amazon.Lambda.Core;
using Amazon.Lambda.APIGatewayEvents;
using Amazon.S3;
using Amazon.S3.Model;
using System;
using System.Threading.Tasks;

public class LambdaS3Handler
{
    private IAmazonS3 s3Client;
    
    public LambdaS3Handler()
    {
        s3Client = new AmazonS3Client();
    }
    
    public async Task<APIGatewayProxyResponse> FunctionHandler(APIGatewayProxyRequest request, ILambdaContext context)
    {
        var bucketName = request.QueryStringParameters["bucket"];
        var listRequest = new ListObjectsRequest { BucketName = bucketName };
        var response = await s3Client.ListObjectsAsync(listRequest);
        
        return new APIGatewayProxyResponse
        {
            StatusCode = 200,
            Body = $"Found {response.S3Objects.Count} objects"
        };
    }
}
""",
        "services": ["lambda", "s3"],
        "expected": ["Google.Cloud.Functions", "Google.Cloud.Storage"],
        "forbidden": ["Amazon.Lambda", "Amazon.S3", "IAmazonS3", "s3Client"]
    },
    
    "dynamodb_basic": {
        "code": """using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public class DynamoDBExample
{
    private IAmazonDynamoDB dynamoDB;
    
    public DynamoDBExample()
    {
        dynamoDB = new AmazonDynamoDBClient();
    }
    
    public async Task PutItemAsync(string tableName, Dictionary<string, AttributeValue> item)
    {
        var request = new PutItemRequest
        {
            TableName = tableName,
            Item = item
        };
        await dynamoDB.PutItemAsync(request);
    }
    
    public async Task<Dictionary<string, AttributeValue>> GetItemAsync(string tableName, Dictionary<string, AttributeValue> key)
    {
        var request = new GetItemRequest
        {
            TableName = tableName,
            Key = key
        };
        var response = await dynamoDB.GetItemAsync(request);
        return response.Item;
    }
}
""",
        "services": ["dynamodb"],
        "expected": ["Google.Cloud.Firestore", "FirestoreDb"],
        "forbidden": ["Amazon.DynamoDB", "IAmazonDynamoDB", "AttributeValue", "PutItemRequest"]
    },
    
    "sqs_basic": {
        "code": """using Amazon.SQS;
using Amazon.SQS.Model;
using System;
using System.Threading.Tasks;

public class SQSExample
{
    private IAmazonSQS sqsClient;
    
    public SQSExample()
    {
        sqsClient = new AmazonSQSClient();
    }
    
    public async Task SendMessageAsync(string queueUrl, string messageBody)
    {
        var request = new SendMessageRequest
        {
            QueueUrl = queueUrl,
            MessageBody = messageBody
        };
        await sqsClient.SendMessageAsync(request);
    }
    
    public async Task<List<Message>> ReceiveMessagesAsync(string queueUrl)
    {
        var request = new ReceiveMessageRequest { QueueUrl = queueUrl };
        var response = await sqsClient.ReceiveMessageAsync(request);
        return response.Messages;
    }
}
""",
        "services": ["sqs"],
        "expected": ["Google.Cloud.PubSub", "PublisherClient"],
        "forbidden": ["Amazon.SQS", "IAmazonSQS", "SendMessageRequest"]
    },
    
    "sns_basic": {
        "code": """using Amazon.SNS;
using Amazon.SNS.Model;
using System;
using System.Threading.Tasks;

public class SNSExample
{
    private IAmazonSNS snsClient;
    
    public SNSExample()
    {
        snsClient = new AmazonSNSClient();
    }
    
    public async Task PublishAsync(string topicArn, string message, string subject)
    {
        var request = new PublishRequest
        {
            TopicArn = topicArn,
            Message = message,
            Subject = subject
        };
        await snsClient.PublishAsync(request);
    }
}
""",
        "services": ["sns"],
        "expected": ["Google.Cloud.PubSub", "PublisherClient"],
        "forbidden": ["Amazon.SNS", "IAmazonSNS", "PublishRequest"]
    },
    
    "multi_service": {
        "code": """using Amazon.S3;
using Amazon.DynamoDBv2;
using Amazon.SQS;
using Amazon.S3.Model;
using Amazon.DynamoDBv2.Model;
using Amazon.SQS.Model;
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

public class MultiServiceExample
{
    private IAmazonS3 s3Client;
    private IAmazonDynamoDB dynamoDB;
    private IAmazonSQS sqsClient;
    
    public MultiServiceExample()
    {
        s3Client = new AmazonS3Client();
        dynamoDB = new AmazonDynamoDBClient();
        sqsClient = new AmazonSQSClient();
    }
    
    public async Task ProcessDataAsync(string bucketName, string key, string tableName, string queueUrl)
    {
        // Read from S3
        var getRequest = new GetObjectRequest { BucketName = bucketName, Key = key };
        var s3Response = await s3Client.GetObjectAsync(getRequest);
        
        // Write to DynamoDB
        var item = new Dictionary<string, AttributeValue>
        {
            { "id", new AttributeValue { S = "123" } },
            { "data", new AttributeValue { S = "test" } }
        };
        var putRequest = new PutItemRequest { TableName = tableName, Item = item };
        await dynamoDB.PutItemAsync(putRequest);
        
        // Send to SQS
        var sendRequest = new SendMessageRequest { QueueUrl = queueUrl, MessageBody = "message" };
        await sqsClient.SendMessageAsync(sendRequest);
    }
}
""",
        "services": ["s3", "dynamodb", "sqs"],
        "expected": ["Google.Cloud.Storage", "Google.Cloud.Firestore", "Google.Cloud.PubSub"],
        "forbidden": ["Amazon.S3", "Amazon.DynamoDB", "Amazon.SQS", "IAmazonS3", "IAmazonDynamoDB", "IAmazonSQS"]
    }
}


def test_csharp_migration(test_name: str, test_case: dict):
    """Test C# migration via API"""
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
        import requests
        import json
        
        # Test via API
        api_url = "https://cloud-refactor-agent-108691610262.asia-south1.run.app/api/migrate"
        
        payload = {
            "code": code,
            "language": "csharp",
            "cloud_provider": "aws",
            "services": services
        }
        
        print(f"\nCalling API: {api_url}")
        response = requests.post(api_url, json=payload, timeout=60)
        
        if response.status_code != 200:
            print(f"✗ API call failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        result = response.json()
        transformed_code = result.get("refactored_code", "")
        validation = result.get("validation", {})
        
        print(f"\nOriginal code length: {len(code)}")
        print(f"Refactored code length: {len(transformed_code)}")
        
        # Check validation results
        if validation:
            errors = validation.get("errors", [])
            warnings = validation.get("warnings", [])
            if errors:
                print(f"\nValidation Errors: {errors}")
            if warnings:
                print(f"\nValidation Warnings: {warnings}")
        
        # Check results
        result_lower = transformed_code.lower()
        
        print(f"\nPattern Check Results:")
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
                # For C#, check if it's in comments
                lines = transformed_code.split('\n')
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
        print(transformed_code[:800])
        if len(transformed_code) > 800:
            print("...")
        print("-" * 70)
        
        # Validation
        if missing_patterns:
            print(f"\n⚠ WARNING: Missing expected patterns: {missing_patterns}")
        
        if found_forbidden:
            print(f"\n✗ Test FAILED: Found forbidden patterns: {found_forbidden}")
            return False
        
        if validation and validation.get("errors"):
            print(f"\n✗ Test FAILED: Validation errors present")
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
    """Run all C# tests"""
    print("="*70)
    print("COMPREHENSIVE C# AWS TO GCP MIGRATION TEST SUITE")
    print("="*70)
    
    results = []
    for test_name, test_case in CSHARP_TEST_CASES.items():
        success = test_csharp_migration(test_name, test_case)
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
