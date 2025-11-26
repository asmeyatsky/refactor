"""
Extensive validation tests for Node.js/JavaScript AWS to GCP migrations
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


def test_s3_nodejs():
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

async function listObjects(bucketName, prefix) {
    const params = {
        Bucket: bucketName,
        Prefix: prefix
    };
    
    try {
        const result = await s3.listObjectsV2(params).promise();
        return result.Contents || [];
    } catch (error) {
        console.error('List error:', error);
        throw error;
    }
}

async function deleteObject(bucketName, key) {
    const params = {
        Bucket: bucketName,
        Key: key
    };
    
    try {
        await s3.deleteObject(params).promise();
        console.log('Object deleted successfully');
    } catch (error) {
        console.error('Delete error:', error);
        throw error;
    }
}

module.exports = {
    uploadFile,
    downloadFile,
    listObjects,
    deleteObject
};
"""
    return test_migration(code, "javascript", ["s3"], "S3 to Cloud Storage - Node.js")


def test_lambda_nodejs():
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
    return test_migration(code, "javascript", ["lambda"], "Lambda to Cloud Functions - Node.js")


def test_dynamodb_nodejs():
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

async function queryItems(tableName, keyConditionExpression, expressionAttributeValues) {
    const params = {
        TableName: tableName,
        KeyConditionExpression: keyConditionExpression,
        ExpressionAttributeValues: expressionAttributeValues
    };
    
    try {
        const result = await dynamodb.query(params).promise();
        return result.Items || [];
    } catch (error) {
        console.error('Query error:', error);
        throw error;
    }
}

async function scanItems(tableName) {
    const params = {
        TableName: tableName
    };
    
    try {
        const result = await dynamodb.scan(params).promise();
        return result.Items || [];
    } catch (error) {
        console.error('Scan error:', error);
        throw error;
    }
}

module.exports = {
    putItem,
    getItem,
    queryItems,
    scanItems
};
"""
    return test_migration(code, "javascript", ["dynamodb"], "DynamoDB to Firestore - Node.js")


def test_sqs_nodejs():
    """Test SQS to Pub/Sub migration for Node.js"""
    code = """
const AWS = require('aws-sdk');

const sqs = new AWS.SQS({
    region: 'us-east-1'
});

async function sendMessage(queueUrl, messageBody, messageAttributes = {}) {
    const params = {
        QueueUrl: queueUrl,
        MessageBody: messageBody,
        MessageAttributes: messageAttributes
    };
    
    try {
        const result = await sqs.sendMessage(params).promise();
        console.log('Message sent:', result.MessageId);
        return result;
    } catch (error) {
        console.error('Send error:', error);
        throw error;
    }
}

async function receiveMessages(queueUrl, maxMessages = 10) {
    const params = {
        QueueUrl: queueUrl,
        MaxNumberOfMessages: maxMessages,
        WaitTimeSeconds: 20
    };
    
    try {
        const result = await sqs.receiveMessage(params).promise();
        return result.Messages || [];
    } catch (error) {
        console.error('Receive error:', error);
        throw error;
    }
}

async function deleteMessage(queueUrl, receiptHandle) {
    const params = {
        QueueUrl: queueUrl,
        ReceiptHandle: receiptHandle
    };
    
    try {
        await sqs.deleteMessage(params).promise();
        console.log('Message deleted');
    } catch (error) {
        console.error('Delete error:', error);
        throw error;
    }
}

module.exports = {
    sendMessage,
    receiveMessages,
    deleteMessage
};
"""
    return test_migration(code, "javascript", ["sqs"], "SQS to Pub/Sub - Node.js")


def test_sns_nodejs():
    """Test SNS to Pub/Sub migration for Node.js"""
    code = """
const AWS = require('aws-sdk');

const sns = new AWS.SNS({
    region: 'us-east-1'
});

async function publishMessage(topicArn, message, subject = null) {
    const params = {
        TopicArn: topicArn,
        Message: message
    };
    
    if (subject) {
        params.Subject = subject;
    }
    
    try {
        const result = await sns.publish(params).promise();
        console.log('Message published:', result.MessageId);
        return result;
    } catch (error) {
        console.error('Publish error:', error);
        throw error;
    }
}

async function subscribeToTopic(topicArn, protocol, endpoint) {
    const params = {
        TopicArn: topicArn,
        Protocol: protocol,
        Endpoint: endpoint
    };
    
    try {
        const result = await sns.subscribe(params).promise();
        console.log('Subscribed:', result.SubscriptionArn);
        return result;
    } catch (error) {
        console.error('Subscribe error:', error);
        throw error;
    }
}

module.exports = {
    publishMessage,
    subscribeToTopic
};
"""
    return test_migration(code, "javascript", ["sns"], "SNS to Pub/Sub - Node.js")


def test_multiple_services_nodejs():
    """Test multiple AWS services migration for Node.js"""
    code = """
const AWS = require('aws-sdk');

const s3 = new AWS.S3();
const dynamodb = new AWS.DynamoDB.DocumentClient();
const sqs = new AWS.SQS();

async function processFileUpload(bucketName, key, tableName, queueUrl) {
    // Download from S3
    const s3Params = {
        Bucket: bucketName,
        Key: key
    };
    const fileData = await s3.getObject(s3Params).promise();
    
    // Store metadata in DynamoDB
    const dbParams = {
        TableName: tableName,
        Item: {
            fileKey: key,
            bucketName: bucketName,
            size: fileData.ContentLength,
            uploadedAt: new Date().toISOString()
        }
    };
    await dynamodb.put(dbParams).promise();
    
    // Send notification via SQS
    const sqsParams = {
        QueueUrl: queueUrl,
        MessageBody: JSON.stringify({
            action: 'file_uploaded',
            fileKey: key,
            bucketName: bucketName
        })
    };
    await sqs.sendMessage(sqsParams).promise();
    
    return { success: true };
}

module.exports = { processFileUpload };
"""
    return test_migration(code, "javascript", ["s3", "dynamodb", "sqs"], "Multiple Services - Node.js")


def run_all_tests():
    """Run all Node.js validation tests"""
    print("\n" + "="*80)
    print("NODE.JS / JAVASCRIPT AWS TO GCP MIGRATION VALIDATION TESTS")
    print("="*80)
    
    tests = [
        ("S3 to Cloud Storage", test_s3_nodejs),
        ("Lambda to Cloud Functions", test_lambda_nodejs),
        ("DynamoDB to Firestore", test_dynamodb_nodejs),
        ("SQS to Pub/Sub", test_sqs_nodejs),
        ("SNS to Pub/Sub", test_sns_nodejs),
        ("Multiple Services", test_multiple_services_nodejs),
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
