# C# (.NET) AWS to GCP Migration Test Cases

This document contains comprehensive C# AWS code examples for testing all supported service migrations.

## Service URL
```
https://cloud-refactor-agent-108691610262.asia-south1.run.app
```

## Test Cases

### 1. S3 Basic

**Input Code:**
```csharp
using Amazon.S3;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.Storage`, `StorageClient`
- Should NOT contain: `Amazon.S3`, `IAmazonS3`, `AmazonS3Client`, `s3Client`

---

### 2. S3 with Configuration

**Input Code:**
```csharp
using Amazon.S3;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.Storage`, `StorageClient`
- Should NOT contain: `Amazon.S3`, `IAmazonS3`, `AmazonS3Client`, `RegionEndpoint`

---

### 3. Lambda Basic

**Input Code:**
```csharp
using Amazon.Lambda.Core;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.Functions`, `IHttpFunction`, `HttpContext`
- Should NOT contain: `Amazon.Lambda`, `ILambdaContext`, `APIGatewayProxy`

---

### 4. Lambda with S3

**Input Code:**
```csharp
using Amazon.Lambda.Core;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.Functions`, `Google.Cloud.Storage`
- Should NOT contain: `Amazon.Lambda`, `Amazon.S3`, `IAmazonS3`, `s3Client`

---

### 5. DynamoDB Basic

**Input Code:**
```csharp
using Amazon.DynamoDBv2;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.Firestore`, `FirestoreDb`
- Should NOT contain: `Amazon.DynamoDB`, `IAmazonDynamoDB`, `AttributeValue`, `PutItemRequest`

---

### 6. SQS Basic

**Input Code:**
```csharp
using Amazon.SQS;
using Amazon.SQS.Model;
using System;
using System.Collections.Generic;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.PubSub`, `PublisherClient`
- Should NOT contain: `Amazon.SQS`, `IAmazonSQS`, `SendMessageRequest`

---

### 7. SNS Basic

**Input Code:**
```csharp
using Amazon.SNS;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.PubSub`, `PublisherClient`
- Should NOT contain: `Amazon.SNS`, `IAmazonSNS`, `PublishRequest`

---

### 8. Multi-Service (S3 + DynamoDB + SQS)

**Input Code:**
```csharp
using Amazon.S3;
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
```

**Expected Output:**
- Should contain: `Google.Cloud.Storage`, `Google.Cloud.Firestore`, `Google.Cloud.PubSub`
- Should NOT contain: `Amazon.S3`, `Amazon.DynamoDB`, `Amazon.SQS`, `IAmazonS3`, `IAmazonDynamoDB`, `IAmazonSQS`

---

## Testing Instructions

1. Go to: https://cloud-refactor-agent-108691610262.asia-south1.run.app
2. Select **Cloud Provider**: AWS
3. Select **Language**: C# (.NET)
4. Paste one of the test cases above
5. Select the appropriate **Services** (e.g., S3, Lambda, DynamoDB, etc.)
6. Click **Migrate**
7. Check the validation results - should show **zero AWS patterns**

## Expected Validation Results

After migration, validation should show:
- ✅ **No AWS patterns found**
- ✅ **GCP APIs correctly used**
- ✅ **Syntax valid**

If you see validation errors, the transformation needs improvement. Please report any issues!
