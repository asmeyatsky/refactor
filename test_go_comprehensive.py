"""
Comprehensive Go language migration test suite
Tests AWS and Azure to GCP migrations for Go code
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

# Comprehensive AWS Go test cases
AWS_GO_TESTS = {
    "s3_basic": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)

func main() {
	sess := session.Must(session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	}))
	
	svc := s3.New(sess)
	
	// Upload file
	bucket := "my-bucket"
	key := "my-file.txt"
	input := &s3.PutObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
		Body:   strings.NewReader("Hello, World!"),
	}
	
	_, err := svc.PutObject(input)
	if err != nil {
		log.Fatal(err)
	}
	
	// Download file
	getInput := &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	}
	
	result, err := svc.GetObject(getInput)
	if err != nil {
		log.Fatal(err)
	}
	defer result.Body.Close()
	
	fmt.Printf("Downloaded: %s\n", result.Body)
}
""",
        "services": ["s3"],
        "expected": ["cloud.google.com/go/storage", "storage.NewClient", "bucket.Object", "NewWriter", "NewReader"],
        "forbidden": ["github.com/aws/aws-sdk-go", "s3.New", "s3.PutObjectInput", "s3.GetObjectInput"]
    },
    
    "s3_list_objects": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
)

func listObjects(bucketName string) error {
	sess := session.Must(session.NewSession())
	svc := s3.New(sess)
	
	input := &s3.ListObjectsV2Input{
		Bucket: aws.String(bucketName),
	}
	
	result, err := svc.ListObjectsV2(input)
	if err != nil {
		return err
	}
	
	for _, obj := range result.Contents {
		fmt.Printf("Key: %s, Size: %d\n", *obj.Key, *obj.Size)
	}
	
	return nil
}
""",
        "services": ["s3"],
        "expected": ["cloud.google.com/go/storage", "bucket.Objects", "Objects(ctx, nil)"],
        "forbidden": ["github.com/aws/aws-sdk-go", "s3.ListObjectsV2Input"]
    },
    
    "lambda_handler": {
        "code": """package main

import (
	"context"
	"fmt"
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

func Handler(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Body:       "Hello, World!",
	}, nil
}

func main() {
	lambda.Start(Handler)
}
""",
        "services": ["lambda"],
        "expected": ["net/http", "http.ResponseWriter", "http.Request", "functions_framework"],
        "forbidden": ["github.com/aws/aws-lambda-go", "lambda.Start", "events.APIGatewayProxyRequest"]
    },
    
    "dynamodb_basic": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
)

func putItem(tableName string, item map[string]interface{}) error {
	sess := session.Must(session.NewSession())
	svc := dynamodb.New(sess)
	
	av, err := dynamodbattribute.MarshalMap(item)
	if err != nil {
		return err
	}
	
	input := &dynamodb.PutItemInput{
		TableName: aws.String(tableName),
		Item:      av,
	}
	
	_, err = svc.PutItem(input)
	return err
}

func getItem(tableName, key string) (map[string]interface{}, error) {
	sess := session.Must(session.NewSession())
	svc := dynamodb.New(sess)
	
	input := &dynamodb.GetItemInput{
		TableName: aws.String(tableName),
		Key: map[string]*dynamodb.AttributeValue{
			"id": {
				S: aws.String(key),
			},
		},
	}
	
	result, err := svc.GetItem(input)
	if err != nil {
		return nil, err
	}
	
	var item map[string]interface{}
	err = dynamodbattribute.UnmarshalMap(result.Item, &item)
	return item, err
}
""",
        "services": ["dynamodb"],
        "expected": ["cloud.google.com/go/firestore", "firestore.NewClient", "Collection", "Doc", "Set", "Get"],
        "forbidden": ["github.com/aws/aws-sdk-go", "dynamodb.New", "dynamodb.PutItemInput", "dynamodb.GetItemInput"]
    },
    
    "sqs_send_receive": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sqs"
)

func sendMessage(queueURL, messageBody string) error {
	sess := session.Must(session.NewSession())
	svc := sqs.New(sess)
	
	input := &sqs.SendMessageInput{
		QueueUrl:    aws.String(queueURL),
		MessageBody: aws.String(messageBody),
	}
	
	_, err := svc.SendMessage(input)
	return err
}

func receiveMessages(queueURL string) ([]*sqs.Message, error) {
	sess := session.Must(session.NewSession())
	svc := sqs.New(sess)
	
	input := &sqs.ReceiveMessageInput{
		QueueUrl:            aws.String(queueURL),
		MaxNumberOfMessages: aws.Int64(10),
	}
	
	result, err := svc.ReceiveMessage(input)
	if err != nil {
		return nil, err
	}
	
	return result.Messages, nil
}
""",
        "services": ["sqs"],
        "expected": ["cloud.google.com/go/pubsub", "pubsub.NewClient", "topic.Publish", "sub.Receive"],
        "forbidden": ["github.com/aws/aws-sdk-go", "sqs.New", "sqs.SendMessageInput", "sqs.ReceiveMessageInput"]
    },
    
    "sns_publish": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sns"
)

func publishMessage(topicARN, message string) error {
	sess := session.Must(session.NewSession())
	svc := sns.New(sess)
	
	input := &sns.PublishInput{
		TopicArn: aws.String(topicARN),
		Message:  aws.String(message),
	}
	
	_, err := svc.Publish(input)
	return err
}
""",
        "services": ["sns"],
        "expected": ["cloud.google.com/go/pubsub", "pubsub.NewClient", "topic.Publish"],
        "forbidden": ["github.com/aws/aws-sdk-go", "sns.New", "sns.PublishInput"]
    },
    
    "multi_service_s3_dynamodb": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/dynamodb"
)

func processFile(bucket, key, tableName string) error {
	sess := session.Must(session.NewSession())
	s3Client := s3.New(sess)
	dynamoClient := dynamodb.New(sess)
	
	// Read from S3
	getInput := &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	}
	result, err := s3Client.GetObject(getInput)
	if err != nil {
		return err
	}
	defer result.Body.Close()
	
	// Write to DynamoDB
	putInput := &dynamodb.PutItemInput{
		TableName: aws.String(tableName),
		Item: map[string]*dynamodb.AttributeValue{
			"key": {S: aws.String(key)},
		},
	}
	_, err = dynamoClient.PutItem(putInput)
	return err
}
""",
        "services": ["s3", "dynamodb"],
        "expected": ["cloud.google.com/go/storage", "cloud.google.com/go/firestore", "storage.NewClient", "firestore.NewClient"],
        "forbidden": ["github.com/aws/aws-sdk-go", "s3.New", "dynamodb.New"]
    }
}

# Comprehensive Azure Go test cases
AZURE_GO_TESTS = {
    "blob_storage_basic": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
)

func main() {
	connectionString := os.Getenv("AZURE_STORAGE_CONNECTION_STRING")
	serviceClient, err := azblob.NewClientFromConnectionString(connectionString, nil)
	if err != nil {
		log.Fatal(err)
	}
	
	containerName := "mycontainer"
	blobName := "myfile.txt"
	
	// Upload blob
	data := []byte("Hello, Azure Blob Storage!")
	_, err = serviceClient.UploadBuffer(context.Background(), containerName, blobName, data, nil)
	if err != nil {
		log.Fatal(err)
	}
	
	// Download blob
	downloadResp, err := serviceClient.DownloadBuffer(context.Background(), containerName, blobName, nil)
	if err != nil {
		log.Fatal(err)
	}
	
	fmt.Printf("Downloaded: %s\n", string(downloadResp))
}
""",
        "services": ["blob_storage"],
        "expected": ["cloud.google.com/go/storage", "storage.NewClient", "bucket.Object", "NewWriter", "NewReader"],
        "forbidden": ["github.com/Azure/azure-sdk-for-go", "azblob.NewClientFromConnectionString", "AZURE_STORAGE_CONNECTION_STRING"]
    },
    
    "cosmos_db_basic": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/Azure/azure-sdk-for-go/sdk/data/azcosmos"
)

func createItem(ctx context.Context, client *azcosmos.Client, databaseName, containerName string, item map[string]interface{}) error {
	database, err := client.NewDatabase(databaseName)
	if err != nil {
		return err
	}
	
	container, err := database.NewContainer(containerName)
	if err != nil {
		return err
	}
	
	_, err = container.CreateItem(ctx, item, nil)
	return err
}

func readItem(ctx context.Context, client *azcosmos.Client, databaseName, containerName, itemID string) (map[string]interface{}, error) {
	database, err := client.NewDatabase(databaseName)
	if err != nil {
		return nil, err
	}
	
	container, err := database.NewContainer(containerName)
	if err != nil {
		return nil, err
	}
	
	item, err := container.ReadItem(ctx, itemID, nil)
	if err != nil {
		return nil, err
	}
	
	return item, nil
}
""",
        "services": ["cosmos_db"],
        "expected": ["cloud.google.com/go/firestore", "firestore.NewClient", "Collection", "Doc", "Set", "Get"],
        "forbidden": ["github.com/Azure/azure-sdk-for-go", "azcosmos.Client", "CreateItem", "ReadItem"]
    },
    
    "service_bus_queue": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/Azure/azure-sdk-for-go/sdk/messaging/azservicebus"
)

func sendMessage(ctx context.Context, connectionString, queueName, message string) error {
	client, err := azservicebus.NewClientWithConnectionString(connectionString, nil)
	if err != nil {
		return err
	}
	
	sender, err := client.NewSender(queueName, nil)
	if err != nil {
		return err
	}
	defer sender.Close(ctx)
	
	sbMessage := &azservicebus.Message{
		Body: []byte(message),
	}
	
	return sender.SendMessage(ctx, sbMessage, nil)
}

func receiveMessages(ctx context.Context, connectionString, queueName string) error {
	client, err := azservicebus.NewClientWithConnectionString(connectionString, nil)
	if err != nil {
		return err
	}
	
	receiver, err := client.NewReceiverForQueue(queueName, nil)
	if err != nil {
		return err
	}
	defer receiver.Close(ctx)
	
	messages, err := receiver.ReceiveMessages(ctx, 10, nil)
	if err != nil {
		return err
	}
	
	for _, msg := range messages {
		fmt.Printf("Received: %s\n", string(msg.Body))
		receiver.CompleteMessage(ctx, msg, nil)
	}
	
	return nil
}
""",
        "services": ["service_bus"],
        "expected": ["cloud.google.com/go/pubsub", "pubsub.NewClient", "topic.Publish", "sub.Receive"],
        "forbidden": ["github.com/Azure/azure-sdk-for-go", "azservicebus.NewClientWithConnectionString", "SERVICEBUS_CONNECTION_STRING"]
    },
    
    "key_vault_secrets": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
)

func getSecret(ctx context.Context, vaultURL, secretName string) (string, error) {
	credential, err := azidentity.NewDefaultAzureCredential(nil)
	if err != nil {
		return "", err
	}
	
	client, err := azsecrets.NewClient(vaultURL, credential, nil)
	if err != nil {
		return "", err
	}
	
	resp, err := client.GetSecret(ctx, secretName, nil)
	if err != nil {
		return "", err
	}
	
	return *resp.Value, nil
}

func setSecret(ctx context.Context, vaultURL, secretName, secretValue string) error {
	credential, err := azidentity.NewDefaultAzureCredential(nil)
	if err != nil {
		return err
	}
	
	client, err := azsecrets.NewClient(vaultURL, credential, nil)
	if err != nil {
		return err
	}
	
	_, err = client.SetSecret(ctx, secretName, secretValue, nil)
	return err
}
""",
        "services": ["key_vault"],
        "expected": ["cloud.google.com/go/secretmanager/apiv1", "secretmanager.NewClient", "AccessSecretVersion", "CreateSecret"],
        "forbidden": ["github.com/Azure/azure-sdk-for-go", "azsecrets.NewClient", "azidentity.NewDefaultAzureCredential", "AZURE_KEY_VAULT_URL"]
    },
    
    "application_insights_telemetry": {
        "code": """package main

import (
	"context"
	"fmt"
	"log"
	"github.com/Azure/azure-sdk-for-go/sdk/monitor/query"
)

func trackEvent(ctx context.Context, instrumentationKey, eventName string, properties map[string]string) error {
	client, err := query.NewMetricsClient(instrumentationKey, nil)
	if err != nil {
		return err
	}
	
	// Track custom event
	// Note: Application Insights Go SDK doesn't have direct TrackEvent
	// This is a simplified example
	fmt.Printf("Tracking event: %s with properties: %v\n", eventName, properties)
	return nil
}

func trackMetric(ctx context.Context, instrumentationKey, metricName string, value float64) error {
	client, err := query.NewMetricsClient(instrumentationKey, nil)
	if err != nil {
		return err
	}
	
	// Track custom metric
	fmt.Printf("Tracking metric: %s = %f\n", metricName, value)
	return nil
}
""",
        "services": ["application_insights"],
        "expected": ["cloud.google.com/go/monitoring/apiv3", "cloud.google.com/go/logging", "monitoring.NewMetricClient", "logging.NewClient"],
        "forbidden": ["github.com/Azure/azure-sdk-for-go", "query.NewMetricsClient", "APPINSIGHTS_INSTRUMENTATION_KEY"]
    },
    
    "multi_service_blob_keyvault": {
        "code": """package main

import (
	"context"
	"log"
	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
	"github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
)

func processWithSecret(ctx context.Context, connectionString, vaultURL, secretName string) error {
	// Get secret from Key Vault
	credential, _ := azidentity.NewDefaultAzureCredential(nil)
	secretClient, _ := azsecrets.NewClient(vaultURL, credential, nil)
	secret, _ := secretClient.GetSecret(ctx, secretName, nil)
	
	// Use secret with Blob Storage
	blobClient, _ := azblob.NewClientFromConnectionString(connectionString, nil)
	data := []byte(*secret.Value)
	_, err := blobClient.UploadBuffer(ctx, "container", "blob.txt", data, nil)
	return err
}
""",
        "services": ["blob_storage", "key_vault"],
        "expected": ["cloud.google.com/go/storage", "cloud.google.com/go/secretmanager/apiv1", "storage.NewClient", "secretmanager.NewClient"],
        "forbidden": ["github.com/Azure/azure-sdk-for-go", "azblob", "azsecrets"]
    }
}


def test_migration(test_name: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single migration case"""
    print(f"\n{'='*70}")
    print(f"Testing: {test_name}")
    print(f"{'='*70}")
    
    try:
        # Submit migration request
        request_data = {
            "code": test_case["code"],
            "language": "go",
            "services": test_case["services"],
            "cloud_provider": "aws" if "aws" in test_name.lower() else "azure"
        }
        
        print(f"Services to migrate: {test_case['services']}")
        print(f"Submitting migration request...")
        
        response = requests.post(
            f"{BASE_URL}/api/migrate",
            json=request_data,
            timeout=300
        )
        
        if response.status_code != 200:
            return {
                "test_name": test_name,
                "success": False,
                "error": f"API returned {response.status_code}: {response.text}"
            }
        
        migration_data = response.json()
        migration_id = migration_data["migration_id"]
        print(f"Migration ID: {migration_id}")
        
        # Poll for completion
        max_wait = 300
        wait_time = 0
        while wait_time < max_wait:
            status_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}")
            if status_response.status_code != 200:
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": f"Failed to get status: {status_response.status_code}"
                }
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "completed":
                print("✓ Migration completed")
                break
            elif status == "failed":
                error = status_data.get("result", {}).get("error", "Unknown error")
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": f"Migration failed: {error}"
                }
            
            time.sleep(2)
            wait_time += 2
            if wait_time % 10 == 0:
                print(f"  Waiting... ({wait_time}s)")
        
        if wait_time >= max_wait:
            return {
                "test_name": test_name,
                "success": False,
                "error": "Migration timed out"
            }
        
        # Get final result
        final_response = requests.get(f"{BASE_URL}/api/migration/{migration_id}")
        final_data = final_response.json()
        
        refactored_code = final_data.get("refactored_code", "")
        validation = final_data.get("validation", {})
        
        if not refactored_code:
            return {
                "test_name": test_name,
                "success": False,
                "error": "No refactored code returned"
            }
        
        print(f"\nRefactored code preview (first 500 chars):")
        print("-" * 70)
        print(refactored_code[:500])
        print("-" * 70)
        
        # Validate results
        result = {
            "test_name": test_name,
            "success": True,
            "refactored_code_length": len(refactored_code),
            "validation": validation
        }
        
        # Check for expected patterns
        missing = []
        for pattern in test_case.get("expected", []):
            if pattern.lower() not in refactored_code.lower():
                missing.append(pattern)
                print(f"✗ Missing expected pattern: {pattern}")
        
        if missing:
            result["missing_patterns"] = missing
            result["success"] = False
        
        # Check for forbidden patterns
        found_forbidden = []
        for pattern in test_case.get("forbidden", []):
            if pattern.lower() in refactored_code.lower():
                found_forbidden.append(pattern)
                print(f"✗ Found forbidden pattern: {pattern}")
        
        if found_forbidden:
            result["forbidden_patterns"] = found_forbidden
            result["success"] = False
        
        # Check validation
        if not validation.get("is_valid", True):
            val_errors = validation.get("errors", [])
            val_warnings = validation.get("warnings", [])
            print(f"⚠ Validation issues:")
            if val_errors:
                print(f"  Errors: {val_errors}")
            if val_warnings:
                print(f"  Warnings: {val_warnings}")
            result["validation_errors"] = val_errors
            result["validation_warnings"] = val_warnings
        
        if not missing and not found_forbidden:
            print(f"✓ All validations passed!")
        
        return result
        
    except Exception as e:
        return {
            "test_name": test_name,
            "success": False,
            "error": f"Failed to get result: {str(e)}"
        }


def run_all_tests():
    """Run all Go migration tests"""
    print("="*70)
    print("COMPREHENSIVE GO LANGUAGE MIGRATION TEST SUITE")
    print("Testing AWS and Azure to GCP migrations for Go")
    print("="*70)
    
    # Check API health
    try:
        health_response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health_response.status_code != 200:
            print(f"✗ API health check failed: {health_response.status_code}")
            return []
        print("✓ API is healthy")
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print(f"  Make sure the backend is running on {BASE_URL}")
        return []
    
    results = []
    
    # Test AWS Go services
    print("\n" + "="*70)
    print("TESTING AWS GO SERVICE MIGRATIONS")
    print("="*70)
    for test_name, test_case in AWS_GO_TESTS.items():
        result = test_migration(f"aws_go_{test_name}", test_case)
        results.append(result)
        time.sleep(1)
    
    # Test Azure Go services
    print("\n" + "="*70)
    print("TESTING AZURE GO SERVICE MIGRATIONS")
    print("="*70)
    for test_name, test_case in AZURE_GO_TESTS.items():
        result = test_migration(f"azure_go_{test_name}", test_case)
        results.append(result)
        time.sleep(1)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("success", False))
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    
    # Service breakdown
    service_results = {}
    for result in results:
        test_name = result.get("test_name", "")
        for service in ["s3", "lambda", "dynamodb", "sqs", "sns", "blob_storage", "cosmos_db", 
                       "service_bus", "key_vault", "application_insights"]:
            if service in test_name:
                if service not in service_results:
                    service_results[service] = {"passed": 0, "failed": 0}
                if result.get("success", False):
                    service_results[service]["passed"] += 1
                else:
                    service_results[service]["failed"] += 1
    
    print("\nService Breakdown:")
    for service, counts in sorted(service_results.items()):
        total_service = counts["passed"] + counts["failed"]
        print(f"  {service}: {counts['passed']}/{total_service} passed")
    
    if failed > 0:
        print("\nFailed tests:")
        for result in results:
            if not result.get("success", False):
                error = result.get("error", "Unknown error")
                missing = result.get("missing_patterns", [])
                forbidden = result.get("forbidden_patterns", [])
                print(f"  ✗ {result['test_name']}")
                if error:
                    print(f"    Error: {error}")
                if missing:
                    print(f"    Missing patterns: {missing}")
                if forbidden:
                    print(f"    Forbidden patterns: {forbidden}")
    
    # Save detailed results
    with open("test_go_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to test_go_results.json")
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if all(r.get("success", False) for r in results) else 1)
