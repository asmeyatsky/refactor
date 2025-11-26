"""
Extensive validation tests for Go AWS to GCP migrations
"""
import requests
import json
import time
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"  # Adjust if needed

def test_migration(code: str, language: str, services: list, description: str) -> Dict[str, Any]:
    """Test a code migration"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"{'='*80}")
    print(f"Language: {language}")
    print(f"Services: {services}")
    print(f"\nInput Code:\n{code}\n")
    
    try:
        # Start migration
        response = requests.post(
            f"{API_BASE_URL}/api/migrate",
            json={
                "code": code,
                "language": language,
                "services": services,
                "cloud_provider": "aws"
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return {"success": False, "error": response.text}
        
        result = response.json()
        migration_id = result.get("migration_id")
        
        if not migration_id:
            print("❌ No migration_id returned")
            return {"success": False, "error": "No migration_id"}
        
        print(f"✓ Migration started: {migration_id}")
        
        # Poll for completion
        max_polls = 60  # 60 seconds max
        poll_count = 0
        
        while poll_count < max_polls:
            time.sleep(1)
            status_response = requests.get(f"{API_BASE_URL}/api/migration/{migration_id}", timeout=10)
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code}")
                break
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "completed":
                print("\n✓ Migration completed!")
                refactored_code = status_data.get("refactored_code") or status_data.get("result", {}).get("refactored_code")
                validation = status_data.get("result", {}).get("validation", {})
                
                print(f"\n{'='*80}")
                print("REFACTORED CODE:")
                print(f"{'='*80}")
                print(refactored_code or "No code returned")
                print(f"\n{'='*80}")
                print("VALIDATION RESULTS:")
                print(f"{'='*80}")
                print(json.dumps(validation, indent=2))
                
                # Check for AWS patterns
                aws_patterns = validation.get("aws_patterns_found", [])
                if aws_patterns:
                    print(f"\n⚠️  AWS Patterns Found: {aws_patterns}")
                else:
                    print("\n✓ No AWS patterns detected")
                
                # Check syntax
                syntax_valid = validation.get("syntax_valid", False)
                if syntax_valid:
                    print("✓ Syntax is valid")
                else:
                    print("❌ Syntax errors detected")
                
                # Check GCP API correctness
                gcp_api_correct = validation.get("gcp_api_correct", False)
                if gcp_api_correct:
                    print("✓ GCP APIs are correctly used")
                else:
                    print("⚠️  GCP API usage may be incorrect")
                
                return {
                    "success": True,
                    "refactored_code": refactored_code,
                    "validation": validation
                }
            elif status == "failed":
                error = status_data.get("result", {}).get("error", "Unknown error")
                print(f"\n❌ Migration failed: {error}")
                return {"success": False, "error": error}
            
            poll_count += 1
        
        print("\n❌ Migration timeout")
        return {"success": False, "error": "Timeout"}
        
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_s3_golang():
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

func listObjects(ctx context.Context, bucketName, prefix string) ([]*s3.Object, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	svc := s3.New(sess)

	result, err := svc.ListObjectsV2WithContext(ctx, &s3.ListObjectsV2Input{
		Bucket: aws.String(bucketName),
		Prefix: aws.String(prefix),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list objects: %w", err)
	}

	return result.Contents, nil
}

func deleteObject(ctx context.Context, bucketName, key string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := s3.New(sess)

	_, err = svc.DeleteObjectWithContext(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("failed to delete object: %w", err)
	}

	fmt.Printf("Object deleted successfully: s3://%s/%s\n", bucketName, key)
	return nil
}
"""
    return test_migration(code, "go", ["s3"], "S3 to Cloud Storage - Go")


def test_lambda_golang():
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
    return test_migration(code, "go", ["lambda"], "Lambda to Cloud Functions - Go")


def test_dynamodb_golang():
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

func queryItems(ctx context.Context, tableName, indexName, keyConditionExpression string, expressionAttributeValues map[string]*dynamodb.AttributeValue) ([]Item, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	svc := dynamodb.New(sess)

	input := &dynamodb.QueryInput{
		TableName:                 aws.String(tableName),
		IndexName:                 aws.String(indexName),
		KeyConditionExpression:    aws.String(keyConditionExpression),
		ExpressionAttributeValues: expressionAttributeValues,
	}

	result, err := svc.QueryWithContext(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to query items: %w", err)
	}

	var items []Item
	for _, itemMap := range result.Items {
		var item Item
		err := dynamodbattribute.UnmarshalMap(itemMap, &item)
		if err != nil {
			return nil, fmt.Errorf("failed to unmarshal item: %w", err)
		}
		items = append(items, item)
	}

	return items, nil
}

func scanItems(ctx context.Context, tableName string) ([]Item, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	svc := dynamodb.New(sess)

	result, err := svc.ScanWithContext(ctx, &dynamodb.ScanInput{
		TableName: aws.String(tableName),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to scan items: %w", err)
	}

	var items []Item
	for _, itemMap := range result.Items {
		var item Item
		err := dynamodbattribute.UnmarshalMap(itemMap, &item)
		if err != nil {
			return nil, fmt.Errorf("failed to unmarshal item: %w", err)
		}
		items = append(items, item)
	}

	return items, nil
}
"""
    return test_migration(code, "go", ["dynamodb"], "DynamoDB to Firestore - Go")


def test_sqs_golang():
    """Test SQS to Pub/Sub migration for Go"""
    code = """package main

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sqs"
)

func sendMessage(ctx context.Context, queueURL, messageBody string, messageAttributes map[string]*sqs.MessageAttributeValue) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := sqs.New(sess)

	input := &sqs.SendMessageInput{
		QueueUrl:       aws.String(queueURL),
		MessageBody:    aws.String(messageBody),
		MessageAttributes: messageAttributes,
	}

	result, err := svc.SendMessageWithContext(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to send message: %w", err)
	}

	fmt.Printf("Message sent successfully: %s\n", *result.MessageId)
	return nil
}

func receiveMessages(ctx context.Context, queueURL string, maxMessages int64) ([]*sqs.Message, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	svc := sqs.New(sess)

	input := &sqs.ReceiveMessageInput{
		QueueUrl:            aws.String(queueURL),
		MaxNumberOfMessages: aws.Int64(maxMessages),
		WaitTimeSeconds:     aws.Int64(20),
	}

	result, err := svc.ReceiveMessageWithContext(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to receive messages: %w", err)
	}

	return result.Messages, nil
}

func deleteMessage(ctx context.Context, queueURL, receiptHandle string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := sqs.New(sess)

	input := &sqs.DeleteMessageInput{
		QueueUrl:      aws.String(queueURL),
		ReceiptHandle: aws.String(receiptHandle),
	}

	_, err = svc.DeleteMessageWithContext(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to delete message: %w", err)
	}

	fmt.Println("Message deleted successfully")
	return nil
}
"""
    return test_migration(code, "go", ["sqs"], "SQS to Pub/Sub - Go")


def test_sns_golang():
    """Test SNS to Pub/Sub migration for Go"""
    code = """package main

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sns"
)

func publishMessage(ctx context.Context, topicARN, message, subject string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	svc := sns.New(sess)

	input := &sns.PublishInput{
		TopicArn: aws.String(topicARN),
		Message:  aws.String(message),
	}

	if subject != "" {
		input.Subject = aws.String(subject)
	}

	result, err := svc.PublishWithContext(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to publish message: %w", err)
	}

	fmt.Printf("Message published successfully: %s\n", *result.MessageId)
	return nil
}

func subscribeToTopic(ctx context.Context, topicARN, protocol, endpoint string) (string, error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return "", fmt.Errorf("failed to create session: %w", err)
	}

	svc := sns.New(sess)

	input := &sns.SubscribeInput{
		TopicArn: aws.String(topicARN),
		Protocol: aws.String(protocol),
		Endpoint: aws.String(endpoint),
	}

	result, err := svc.SubscribeWithContext(ctx, input)
	if err != nil {
		return "", fmt.Errorf("failed to subscribe: %w", err)
	}

	fmt.Printf("Subscribed successfully: %s\n", *result.SubscriptionArn)
	return *result.SubscriptionArn, nil
}
"""
    return test_migration(code, "go", ["sns"], "SNS to Pub/Sub - Go")


def test_multiple_services_golang():
    """Test multiple AWS services migration for Go"""
    code = """package main

import (
	"context"
	"fmt"
	"io"
	"os"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/dynamodb"
	"github.com/aws/aws-sdk-go/service/dynamodb/dynamodbattribute"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/sqs"
)

func processFileUpload(ctx context.Context, bucketName, key, tableName, queueURL string) error {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1"),
	})
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	s3Client := s3.New(sess)
	dynamoClient := dynamodb.New(sess)
	sqsClient := sqs.New(sess)

	// Download from S3
	result, err := s3Client.GetObjectWithContext(ctx, &s3.GetObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("failed to get object: %w", err)
	}
	defer result.Body.Close()

	// Store metadata in DynamoDB
	item := map[string]interface{}{
		"fileKey":    key,
		"bucketName": bucketName,
		"size":       *result.ContentLength,
	}

	av, err := dynamodbattribute.MarshalMap(item)
	if err != nil {
		return fmt.Errorf("failed to marshal item: %w", err)
	}

	_, err = dynamoClient.PutItemWithContext(ctx, &dynamodb.PutItemInput{
		TableName: aws.String(tableName),
		Item:      av,
	})
	if err != nil {
		return fmt.Errorf("failed to put item: %w", err)
	}

	// Send notification via SQS
	messageBody := fmt.Sprintf(`{"action":"file_uploaded","fileKey":"%s","bucketName":"%s"}`, key, bucketName)
	_, err = sqsClient.SendMessageWithContext(ctx, &sqs.SendMessageInput{
		QueueUrl:    aws.String(queueURL),
		MessageBody: aws.String(messageBody),
	})
	if err != nil {
		return fmt.Errorf("failed to send message: %w", err)
	}

	fmt.Println("File processed successfully")
	return nil
}
"""
    return test_migration(code, "go", ["s3", "dynamodb", "sqs"], "Multiple Services - Go")


def run_all_tests():
    """Run all Go validation tests"""
    print("\n" + "="*80)
    print("GO (GOLANG) AWS TO GCP MIGRATION VALIDATION TESTS")
    print("="*80)
    
    tests = [
        ("S3 to Cloud Storage", test_s3_golang),
        ("Lambda to Cloud Functions", test_lambda_golang),
        ("DynamoDB to Firestore", test_dynamodb_golang),
        ("SQS to Pub/Sub", test_sqs_golang),
        ("SNS to Pub/Sub", test_sns_golang),
        ("Multiple Services", test_multiple_services_golang),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append({
                "test": test_name,
                "success": result.get("success", False),
                "error": result.get("error")
            })
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {str(e)}")
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
        status = "✓ PASS" if result["success"] else "❌ FAIL"
        print(f"{status}: {result['test']}")
        if result.get("error"):
            print(f"   Error: {result['error']}")
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return results


if __name__ == "__main__":
    run_all_tests()
