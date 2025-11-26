"""
Direct validation tests for Node.js and Go AWS to GCP migrations
Tests the transformation engine directly without API server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
from application.use_cases.validate_gcp_code_use_case import ValidateGCPCodeUseCase

def test_transformation(code: str, language: str, services: list, description: str):
    """Test code transformation directly"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"{'='*80}")
    print(f"Language: {language}")
    print(f"Services: {services}")
    print(f"\n{'='*80}")
    print("INPUT CODE:")
    print(f"{'='*80}")
    print(code)
    
    try:
        # Create transformation engine
        engine = ExtendedASTTransformationEngine()
        
        # Create transformation recipe
        transformation_recipe = {
            "operation": "service_migration",
            "service_type": services[0] if services else "s3_to_gcs",
            "target_api": "GCP"
        }
        
        # Transform code
        print(f"\n{'='*80}")
        print("TRANSFORMING CODE...")
        print(f"{'='*80}")
        
        transformed_code, variable_mapping = engine.transform_code(
            code, 
            language, 
            transformation_recipe
        )
        
        print(f"\n{'='*80}")
        print("TRANSFORMED CODE:")
        print(f"{'='*80}")
        print(transformed_code)
        
        # Validate transformed code
        print(f"\n{'='*80}")
        print("VALIDATING CODE...")
        print(f"{'='*80}")
        
        validator = ValidateGCPCodeUseCase()
        
        def progress_callback(message, percentage):
            print(f"  [{percentage:.1f}%] {message}")
        
        validation_result = validator.validate(
            transformed_code,
            language=language,
            progress_callback=progress_callback
        )
        
        print(f"\n{'='*80}")
        print("VALIDATION RESULTS:")
        print(f"{'='*80}")
        print(f"Valid: {validation_result.is_valid}")
        print(f"Syntax Valid: {validation_result.syntax_valid}")
        print(f"GCP API Correct: {validation_result.gcp_api_correct}")
        print(f"AWS Patterns Found: {len(validation_result.aws_patterns_found)}")
        
        if validation_result.aws_patterns_found:
            print(f"\n⚠️  AWS Patterns Detected:")
            for pattern in validation_result.aws_patterns_found:
                print(f"  - {pattern}")
        else:
            print("\n✓ No AWS patterns detected")
        
        if validation_result.errors:
            print(f"\n❌ Errors:")
            for error in validation_result.errors:
                print(f"  - {error}")
        
        if validation_result.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in validation_result.warnings:
                print(f"  - {warning}")
        
        # Check for GCP patterns
        gcp_keywords = [
            'google.cloud', 'Storage', 'Firestore', 'PubSub', 
            '@google-cloud', 'cloud.google.com/go'
        ]
        found_gcp = []
        code_lower = transformed_code.lower()
        for keyword in gcp_keywords:
            if keyword.lower() in code_lower:
                found_gcp.append(keyword)
        
        if found_gcp:
            print(f"\n✓ GCP Patterns Found:")
            for pattern in found_gcp:
                print(f"  - {pattern}")
        else:
            print("\n⚠️  No GCP patterns detected - may need manual review")
        
        success = (
            validation_result.is_valid and
            validation_result.syntax_valid and
            len(validation_result.aws_patterns_found) == 0
        )
        
        return {
            "success": success,
            "transformed_code": transformed_code,
            "validation": validation_result,
            "gcp_patterns_found": found_gcp
        }
        
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_nodejs_s3():
    """Test S3 to Cloud Storage migration for Node.js"""
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

async function downloadFile(bucketName, key, filePath) {
    const params = {
        Bucket: bucketName,
        Key: key
    };
    
    try {
        const result = await s3.getObject(params).promise();
        require('fs').writeFileSync(filePath, result.Body);
        console.log('File downloaded successfully');
        return result;
    } catch (error) {
        console.error('Download error:', error);
        throw error;
    }
}

module.exports = {
    uploadFile,
    downloadFile
};
"""
    return test_transformation(code, "javascript", ["s3"], "S3 to Cloud Storage - Node.js")


def test_nodejs_lambda():
    """Test Lambda to Cloud Functions migration for Node.js"""
    code = """
exports.handler = async (event, context) => {
    console.log('Event:', JSON.stringify(event));
    console.log('Context:', context);
    
    const response = {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        body: JSON.stringify({
            message: 'Hello from Lambda!',
            event: event,
            requestId: context.requestId
        })
    };
    
    return response;
};
"""
    return test_transformation(code, "javascript", ["lambda"], "Lambda to Cloud Functions - Node.js")


def test_nodejs_dynamodb():
    """Test DynamoDB to Firestore migration for Node.js"""
    code = """
const AWS = require('aws-sdk');

const dynamodb = new AWS.DynamoDB.DocumentClient({
    region: 'us-east-1'
});

async function putItem(tableName, item) {
    const params = {
        TableName: tableName,
        Item: item
    };
    
    try {
        const result = await dynamodb.put(params).promise();
        console.log('Item put successfully');
        return result;
    } catch (error) {
        console.error('Put error:', error);
        throw error;
    }
}

async function getItem(tableName, key) {
    const params = {
        TableName: tableName,
        Key: key
    };
    
    try {
        const result = await dynamodb.get(params).promise();
        return result.Item;
    } catch (error) {
        console.error('Get error:', error);
        throw error;
    }
}

module.exports = {
    putItem,
    getItem
};
"""
    return test_transformation(code, "javascript", ["dynamodb"], "DynamoDB to Firestore - Node.js")


def test_golang_s3():
    """Test S3 to Cloud Storage migration for Go"""
    code = """package main

import (
	"context"
	"fmt"
	"io"
	"os"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)

func uploadFile(ctx context.Context, bucketName, key, filePath string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := s3.New(sess)

	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	_, err = svc.PutObjectWithContext(ctx, &s3.PutObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(key),
		Body:   file,
	})
	if err != nil {
		return fmt.Errorf("failed to upload file: %w", err)
	}

	fmt.Printf("File uploaded successfully: s3://%s/%s\n", bucketName, key)
	return nil
}

func downloadFile(ctx context.Context, bucketName, key, filePath string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := s3.New(sess)

	result, err := svc.GetObjectWithContext(ctx, &s3.GetObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("failed to download file: %w", err)
	}
	defer result.Body.Close()

	outFile, err := os.Create(filePath)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer outFile.Close()

	_, err = io.Copy(outFile, result.Body)
	if err != nil {
		return fmt.Errorf("failed to write file: %w", err)
	}

	fmt.Printf("File downloaded successfully: %s\n", filePath)
	return nil
}
"""
    return test_transformation(code, "go", ["s3"], "S3 to Cloud Storage - Go")


def test_golang_lambda():
    """Test Lambda to Cloud Functions migration for Go"""
    code = """package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

type Response struct {
	StatusCode int               `json:"statusCode"`
	Headers    map[string]string `json:"headers"`
	Body       string            `json:"body"`
}

func Handler(ctx context.Context, request events.APIGatewayProxyRequest) (Response, error) {
	log.Printf("Processing request: %s", request.RequestContext.RequestID)
	log.Printf("Event: %+v", request)

	body := map[string]interface{}{
		"message":   "Hello from Lambda!",
		"requestId": request.RequestContext.RequestID,
		"path":      request.Path,
		"method":    request.HTTPMethod,
	}

	bodyJSON, err := json.Marshal(body)
	if err != nil {
		return Response{
			StatusCode: 500,
			Body:       fmt.Sprintf(`{"error": "%s"}`, err.Error()),
		}, err
	}

	return Response{
		StatusCode: 200,
		Headers: map[string]string{
			"Content-Type":                "application/json",
			"Access-Control-Allow-Origin": "*",
		},
		Body: string(bodyJSON),
	}, nil
}

func main() {
	lambda.Start(Handler)
}
"""
    return test_transformation(code, "go", ["lambda"], "Lambda to Cloud Functions - Go")


def test_golang_dynamodb():
    """Test DynamoDB to Firestore migration for Go"""
    code = """package main

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

type Item struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
}

func putItem(ctx context.Context, tableName string, item Item) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := dynamodb.New(sess)

	av, err := dynamodbattribute.MarshalMap(item)
	if err != nil {
		return fmt.Errorf("failed to marshal item: %w", err)
	}

	input := &dynamodb.PutItemInput{
		Item:      av,
		TableName: aws.String(tableName),
	}

	_, err = svc.PutItemWithContext(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to put item: %w", err)
	}

	fmt.Printf("Item put successfully: %s\n", item.ID)
	return nil
}

func getItem(ctx context.Context, tableName, key string) (*Item, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	svc := dynamodb.New(sess)

	result, err := svc.GetItemWithContext(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(tableName),
		Key: map[string]*dynamodb.AttributeValue{
			"id": {
				S: aws.String(key),
			},
		},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get item: %w", err)
	}

	if result.Item == nil {
		return nil, fmt.Errorf("item not found")
	}

	var item Item
	err = dynamodbattribute.UnmarshalMap(result.Item, &item)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal item: %w", err)
	}

	return &item, nil
}
"""
    return test_transformation(code, "go", ["dynamodb"], "DynamoDB to Firestore - Go")


def run_all_tests():
    """Run all validation tests"""
    print("\n" + "="*80)
    print("NODE.JS AND GO AWS TO GCP MIGRATION VALIDATION TESTS")
    print("="*80)
    
    tests = [
        ("Node.js - S3 to Cloud Storage", test_nodejs_s3),
        ("Node.js - Lambda to Cloud Functions", test_nodejs_lambda),
        ("Node.js - DynamoDB to Firestore", test_nodejs_dynamodb),
        ("Go - S3 to Cloud Storage", test_golang_s3),
        ("Go - Lambda to Cloud Functions", test_golang_lambda),
        ("Go - DynamoDB to Firestore", test_golang_dynamodb),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append({
                "test": test_name,
                "success": result.get("success", False),
                "error": result.get("error"),
                "aws_patterns": len(result.get("validation", {}).aws_patterns_found) if result.get("validation") else 0,
                "gcp_patterns": len(result.get("gcp_patterns_found", []))
            })
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test_name,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for result in results:
        status = "✓ PASS" if result.get("success") else "❌ FAIL"
        print(f"{status}: {result['test']}")
        if result.get("aws_patterns", 0) > 0:
            print(f"   ⚠️  AWS patterns remaining: {result['aws_patterns']}")
        if result.get("gcp_patterns", 0) > 0:
            print(f"   ✓ GCP patterns found: {result['gcp_patterns']}")
        if result.get("error"):
            print(f"   Error: {result['error']}")
    
    passed = sum(1 for r in results if r.get("success"))
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return results


if __name__ == "__main__":
    # Set GEMINI_API_KEY if not set (for testing)
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not set. Some transformations may fail.")
        print("   Set it as an environment variable to test with Gemini API.")
    
    run_all_tests()
