# Java AWS to GCP Migration Test Cases

This document contains comprehensive Java AWS code examples for testing all supported service migrations.

## Service URL
```
https://cloud-refactor-agent-108691610262.asia-south1.run.app
```

## Test Cases

### 1. S3 Basic (AWS SDK v1)

**Input Code:**
```java
import com.amazonaws.services.s3.AmazonS3;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.storage`, `Storage`, `StorageOptions`
- Should NOT contain: `com.amazonaws`, `AmazonS3`, `S3Client`, `s3Client`, `.s3.`

---

### 2. S3 SDK v2

**Input Code:**
```java
import software.amazon.awssdk.services.s3.S3Client;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.storage`, `Storage`
- Should NOT contain: `S3Client`, `s3Client`, `amazonaws`, `.s3.`

---

### 3. Lambda Basic

**Input Code:**
```java
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import java.util.Map;

public class LambdaHandler implements RequestHandler<Map<String, Object>, Map<String, Object>> {
    @Override
    public Map<String, Object> handleRequest(Map<String, Object> input, Context context) {
        context.getLogger().log("Processing request: " + input);
        return Map.of("statusCode", 200, "body", "Hello from Lambda!");
    }
}
```

**Expected Output:**
- Should contain: `com.google.cloud.functions`, `HttpFunction`, `HttpRequest`, `HttpResponse`
- Should NOT contain: `com.amazonaws`, `RequestHandler`, `ILambdaContext`, `Context`

---

### 4. Lambda with S3

**Input Code:**
```java
import com.amazonaws.services.lambda.runtime.Context;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.functions`, `com.google.cloud.storage`
- Should NOT contain: `com.amazonaws`, `RequestHandler`, `AmazonS3`, `s3Client`

---

### 5. DynamoDB Basic

**Input Code:**
```java
import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.firestore`, `Firestore`
- Should NOT contain: `com.amazonaws`, `AmazonDynamoDB`, `AttributeValue`, `PutItemRequest`

---

### 6. SQS Basic

**Input Code:**
```java
import com.amazonaws.services.sqs.AmazonSQS;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.pubsub`, `PublisherClient`
- Should NOT contain: `com.amazonaws`, `AmazonSQS`, `SendMessageRequest`

---

### 7. SNS Basic

**Input Code:**
```java
import com.amazonaws.services.sns.AmazonSNS;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.pubsub`, `PublisherClient`
- Should NOT contain: `com.amazonaws`, `AmazonSNS`, `PublishRequest`

---

### 8. Multi-Service (S3 + DynamoDB + SQS)

**Input Code:**
```java
import com.amazonaws.services.s3.AmazonS3;
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
```

**Expected Output:**
- Should contain: `com.google.cloud.storage`, `com.google.cloud.firestore`, `com.google.cloud.pubsub`
- Should NOT contain: `com.amazonaws`, `AmazonS3`, `AmazonDynamoDB`, `AmazonSQS`

---

## Testing Instructions

1. Go to: https://cloud-refactor-agent-108691610262.asia-south1.run.app
2. Select **Cloud Provider**: AWS
3. Select **Language**: Java
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
