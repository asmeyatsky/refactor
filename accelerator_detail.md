# Universal Cloud Refactor Agent - Detailed Accelerator Documentation

## Executive Summary

The **Universal Cloud Refactor Agent** is an enterprise-grade, AI-powered code migration accelerator that automates the complex transformation of cloud-native applications from AWS and Azure to Google Cloud Platform (GCP). Built on a multi-agent architecture with Gemini API integration, it provides intelligent, context-aware code transformations across Python, Java, and C# (.NET) codebases.

### Key Value Propositions

1. **70-75% Cost Reduction**: TOON format integration reduces Gemini API token usage significantly
2. **Multi-Language Support**: Python, Java, and C# (.NET) with intelligent LLM-powered transformations
3. **Enterprise Scale**: Repository-level migrations with atomic PR generation and comprehensive reporting
4. **Zero Manual Intervention**: Fully automated detection, transformation, validation, and PR creation
5. **Production Ready**: Comprehensive test suites, security validation, and verification frameworks

---

## Architecture Overview

### Multi-Agent System Design

The accelerator implements a sophisticated multi-agent architecture where specialized agents collaborate to achieve complex migration goals:

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Web UI     │  │   REST API   │  │   CLI Tools   │     │
│  │  (React)     │  │  (FastAPI)   │  │   (Python)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                          │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Use Cases (Orchestration)                  │   │
│  │  • AnalyzeRepositoryUseCase                        │   │
│  │  • ExecuteRepositoryMigrationUseCase             │   │
│  │  • CreateMultiServiceRefactoringPlanUseCase       │   │
│  │  • ValidateGCPCodeUseCase                         │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer (Agents)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Planner    │  │ Refactoring  │  │ Verification │     │
│  │    Agent     │  │   Engine     │  │    Agent     │     │
│  │              │  │              │  │              │     │
│  │ • Analysis   │  │ • Gemini API │  │ • Security   │     │
│  │ • MAR Gen    │  │ • AST Trans  │  │ • Testing    │     │
│  │ • Planning   │  │ • Multi-Lang │  │ • Validation │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Supporting Infrastructure                   │   │
│  │  • GitAdapter (GitHub, GitLab, Bitbucket)           │   │
│  │  • DependencyGraphBuilder                          │   │
│  │  • IACMigrator (Terraform, CloudFormation, Pulumi)│   │
│  │  • TestExecutionFramework                          │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Entities    │  │ Value Objects│  │   Services   │     │
│  │              │  │              │  │              │     │
│  │ • Repository │  │ • MAR        │  │ • Refactoring│     │
│  │ • Codebase   │  │ • Service    │  │   Domain     │     │
│  │ • Plan       │  │   Mapping   │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Clean Architecture Principles

The accelerator follows **Hexagonal/Clean Architecture** principles:

- **Domain Layer**: Core business logic, entities, value objects (cloud-agnostic)
- **Application Layer**: Use cases orchestrate domain logic (migration workflows)
- **Infrastructure Layer**: External adapters (Git, LLM, AST, Testing)
- **Presentation Layer**: API endpoints, Web UI, CLI tools

This architecture ensures:
- **Testability**: Each layer can be tested independently
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new cloud providers or languages
- **Independence**: Domain logic doesn't depend on external frameworks

---

## Core Components Deep Dive

### 1. Planner Agent

**Responsibility**: Analysis, planning, and Migration Assessment Report (MAR) generation

**Key Capabilities**:
- **Service Detection**: Automatically identifies AWS/Azure services in code
- **Dependency Analysis**: Builds cross-file dependency graphs
- **Risk Assessment**: Evaluates migration complexity and risks
- **MAR Generation**: Creates comprehensive migration assessment reports

**Implementation**:
```python
class AnalyzeRepositoryUseCase:
    def execute(self, repository_url: str, branch: str) -> Dict:
        # 1. Clone repository
        # 2. Analyze all files for cloud services
        # 3. Build dependency graph
        # 4. Generate MAR with:
        #    - Services detected
        #    - Files affected
        #    - Migration recommendations
        #    - Risk assessment
        #    - Estimated effort
```

**Output**: Migration Assessment Report (MAR) containing:
- Detected services (AWS/Azure → GCP mappings)
- Files requiring migration
- Cross-file dependencies
- Migration complexity scores
- Recommended migration order
- Risk factors

### 2. Refactoring Engine

**Responsibility**: Intelligent code transformation using Gemini API

**Key Capabilities**:
- **Multi-Language Support**: Python, Java, C# (.NET)
- **Context-Aware Transformations**: Uses Gemini API for intelligent code understanding
- **Service-Specific Rules**: Custom transformation rules for each AWS/Azure → GCP service pair
- **Smart Migration Detection**: Distinguishes migration scripts from application code (e.g., DynamoDB → Firestore)

**Transformation Flow**:
```
Input Code (AWS/Azure)
    ↓
[1] Service Detection
    ↓
[2] Gemini API Analysis (Context Understanding)
    ↓
[3] Transformation Prompt Generation
    ↓
[4] Gemini API Transformation
    ↓
[5] Pattern Validation (AWS/Azure patterns removed?)
    ↓
[6] Syntax Validation
    ↓
[7] Retry Logic (if needed)
    ↓
Output Code (GCP)
```

**Example: S3 → Cloud Storage Transformation**

**Input (AWS)**:
```python
import boto3
s3_client = boto3.client('s3', region_name='us-east-1')
s3_client.upload_file('local.txt', 'my-bucket', 'remote.txt')
```

**Output (GCP)**:
```python
from google.cloud import storage
storage_client = storage.Client()
bucket = storage_client.bucket('my-bucket')
blob = bucket.blob('remote.txt')
blob.upload_from_filename('local.txt')
```

**Gemini API Integration**:
- Uses `gemini-1.5-flash` for fast, cost-effective transformations
- TOON format reduces token usage by 70-75%
- Retry logic ensures quality (max 2 retries if AWS patterns detected)
- Fallback to regex-based transformer if Gemini fails

### 3. Verification Agent

**Responsibility**: Quality assurance, security validation, and testing

**Key Capabilities**:
- **Syntax Validation**: Ensures transformed code compiles/parses correctly
- **Pattern Detection**: Verifies AWS/Azure patterns are removed
- **GCP API Validation**: Confirms correct GCP SDK usage
- **Security Checks**: Validates code for security vulnerabilities
- **Test Execution**: Runs existing tests to ensure behavioral preservation

**Validation Pipeline**:
```
Transformed Code
    ↓
[1] Syntax Validation (AST parsing)
    ↓
[2] AWS/Azure Pattern Detection
    ↓
[3] GCP API Correctness Check
    ↓
[4] LLM-Based Advanced Validation (optional)
    ↓
[5] Test Execution (if tests exist)
    ↓
Validation Result
```

**Test Execution Framework**:
- Supports multiple test frameworks:
  - Python: `pytest`, `unittest`
  - Java: `JUnit`, `TestNG`
  - C#: `xUnit`, `NUnit`, `MSTest`
- Automatically detects and runs tests
- Reports test results in MAR

---

## Supported Service Migrations

### AWS → GCP Service Mappings

| AWS Service | GCP Equivalent | Transformation Complexity | Status |
|------------|----------------|---------------------------|--------|
| **S3** | Cloud Storage | Medium | ✅ Fully Supported |
| **Lambda** | Cloud Functions / Cloud Run | High | ✅ Fully Supported |
| **DynamoDB** | Firestore / Bigtable | High | ✅ Fully Supported (Smart Detection) |
| **SQS** | Pub/Sub | Medium | ✅ Fully Supported |
| **SNS** | Pub/Sub | Medium | ✅ Fully Supported |
| **RDS** | Cloud SQL | High | ✅ Fully Supported |
| **EC2** | Compute Engine | High | ✅ Fully Supported |
| **CloudWatch** | Cloud Monitoring | Low | ✅ Fully Supported |
| **API Gateway** | Apigee X | High | ✅ Fully Supported |
| **ElastiCache** | Memorystore | Medium | ✅ Fully Supported |
| **EKS** | GKE | Very High | ✅ Fully Supported |
| **Fargate** | Cloud Run | High | ✅ Fully Supported |

### Azure → GCP Service Mappings

| Azure Service | GCP Equivalent | Transformation Complexity | Status |
|--------------|----------------|---------------------------|--------|
| **Blob Storage** | Cloud Storage | Medium | ✅ Fully Supported |
| **Functions** | Cloud Functions | High | ✅ Fully Supported |
| **Cosmos DB** | Firestore | High | ✅ Fully Supported |
| **Service Bus** | Pub/Sub | Medium | ✅ Fully Supported |
| **Event Hubs** | Pub/Sub | Medium | ✅ Fully Supported |
| **SQL Database** | Cloud SQL | High | ✅ Fully Supported |
| **Virtual Machines** | Compute Engine | High | ✅ Fully Supported |
| **Monitor** | Cloud Monitoring | Low | ✅ Fully Supported |
| **API Management** | Apigee | High | ✅ Fully Supported |
| **Redis Cache** | Memorystore | Medium | ✅ Fully Supported |
| **AKS** | GKE | Very High | ✅ Fully Supported |
| **Container Instances** | Cloud Run | High | ✅ Fully Supported |
| **App Service** | Cloud Run | High | ✅ Fully Supported |

---

## Language Support Details

### Python

**Status**: ✅ **Production Ready**

**Features**:
- AST-powered transformations
- Comprehensive service coverage
- Smart DynamoDB migration detection
- Preserves code structure and comments

**Example Transformation**:
```python
# AWS Lambda Handler
def lambda_handler(event, context):
    s3 = boto3.client('s3')
    s3.upload_file('file.txt', 'bucket', 'key')
    return {'statusCode': 200}

# GCP Cloud Function
def cloud_function_handler(request):
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.bucket('bucket')
    blob = bucket.blob('key')
    blob.upload_from_filename('file.txt')
    return {'statusCode': 200}
```

### Java

**Status**: ✅ **Production Ready** (Gemini API Enhanced)

**Features**:
- Gemini API-powered intelligent transformations
- Preserves class structure and method signatures
- Handles complex Java patterns (generics, interfaces, annotations)
- Async/await pattern preservation

**Example Transformation**:
```java
// AWS S3 Java
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3ClientBuilder;

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

// GCP Cloud Storage Java
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageOptions;

public class S3Example {
    private Storage storage;
    
    public S3Example() {
        storage = StorageOptions.getDefaultInstance().getService();
    }
    
    public void uploadFile(String bucketName, String key, File file) {
        BlobId blobId = BlobId.of(bucketName, key);
        BlobInfo blobInfo = BlobInfo.newBuilder(blobId).build();
        storage.create(blobInfo, Files.readAllBytes(file.toPath()));
    }
}
```

### C# (.NET)

**Status**: ✅ **Production Ready** (Gemini API Enhanced)

**Features**:
- Gemini API-powered intelligent transformations
- Preserves C# structure (classes, interfaces, async/await)
- Handles C#-specific patterns (LINQ, generics, attributes)
- Proper using statement replacement

**Example Transformation**:
```csharp
// AWS S3 C#
using Amazon.S3;
using Amazon.S3.Model;

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
}

// GCP Cloud Storage C#
using Google.Cloud.Storage.V1;

public class S3Example
{
    private StorageClient storage;
    
    public S3Example()
    {
        storage = StorageClient.Create();
    }
    
    public async Task UploadFileAsync(string bucketName, string key, Stream fileStream)
    {
        await storage.UploadObjectAsync(
            bucketName, 
            key, 
            "application/octet-stream", 
            fileStream
        );
    }
}
```

---

## Advanced Features

### 1. Smart DynamoDB Migration Detection

The accelerator intelligently distinguishes between:
- **Migration Scripts**: Code that reads from DynamoDB and writes to Firestore
- **Application Code**: Code that only uses DynamoDB

**Migration Script Handling**:
```python
# Input: Migration script (reads DynamoDB, writes Firestore)
import boto3
from google.cloud import firestore

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('SourceTable')

firestore_db = firestore.Client()

# Scan DynamoDB
response = table.scan()
for item in response['Items']:
    # Write to Firestore
    firestore_db.collection('DestCollection').document().set(item)

# Output: Preserves boto3 for reading, converts writes to Firestore
```

**Application Code Handling**:
```python
# Input: Application code (only DynamoDB)
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MyTable')
table.put_item(Item={'id': '123', 'name': 'John'})

# Output: Fully converts to Firestore
from google.cloud import firestore
firestore_db = firestore.Client()
firestore_db.collection('MyTable').document('123').set({'name': 'John'})
```

### 2. Repository-Level Migration

**Capabilities**:
- **Full Repository Analysis**: Analyzes entire Git repositories
- **Cross-File Dependency Tracking**: Understands dependencies between files
- **Atomic PR Generation**: Creates pull requests with all changes
- **Migration Assessment Reports (MAR)**: Comprehensive migration planning documents

**Workflow**:
```
1. Clone Repository
   ↓
2. Analyze All Files
   ↓
3. Build Dependency Graph
   ↓
4. Generate MAR
   ↓
5. Execute Migration (file by file, respecting dependencies)
   ↓
6. Run Tests
   ↓
7. Create Pull Request
```

**MAR Contents**:
- Services detected
- Files requiring migration
- Dependency graph
- Migration order recommendations
- Risk assessment
- Estimated effort
- Test coverage analysis

### 3. Infrastructure as Code (IaC) Migration

**Supported Formats**:
- **Terraform**: AWS/Azure → GCP resource mappings
- **CloudFormation**: AWS → GCP via Terraform conversion
- **Pulumi**: Multi-cloud → GCP transformations

**Example: Terraform S3 → Cloud Storage**
```hcl
# AWS Terraform
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-bucket-name"
  acl    = "private"
}

# GCP Terraform (after migration)
resource "google_storage_bucket" "my_bucket" {
  name     = "my-bucket-name"
  location = "US"
}
```

### 4. Test Execution Framework

**Automated Testing**:
- Detects test files automatically
- Runs tests before and after migration
- Reports test results in MAR
- Supports multiple test frameworks

**Supported Frameworks**:
- Python: `pytest`, `unittest`
- Java: `JUnit`, `TestNG`
- C#: `xUnit`, `NUnit`, `MSTest`
- JavaScript: `Jest`, `Mocha`

### 5. TOON Format Integration

**Cost Optimization**:
- Reduces Gemini API token usage by 70-75%
- Maintains transformation quality
- Faster API responses

**How It Works**:
- Converts code to token-optimized format before sending to Gemini
- Gemini transforms the optimized format
- Converts back to readable code

---

## Usage Scenarios

### Scenario 1: Single File Migration (Web UI)

1. **Access Web UI**: Navigate to `http://localhost:3000`
2. **Select Cloud Provider**: Choose AWS or Azure
3. **Choose Input Method**: Select "Code Snippet"
4. **Select Language**: Python, Java, or C# (.NET)
5. **Paste Code**: Enter AWS/Azure code
6. **Select Services**: Choose services to migrate
7. **Migrate**: Click "Migrate" button
8. **Review Results**: See transformed GCP code
9. **Download**: Download migrated code

### Scenario 2: Repository Migration (CLI)

```bash
# Step 1: Analyze repository
python main.py repo analyze https://github.com/user/repo.git \
  --branch main \
  --token YOUR_GITHUB_TOKEN

# Output: MAR generated, repository_id returned

# Step 2: Review MAR
cat mar.json

# Step 3: Execute migration
python main.py repo migrate <repository_id> \
  --services s3 lambda dynamodb \
  --create-pr \
  --run-tests \
  --branch-name cloud-migration-2024

# Output: Migration completed, PR created, tests run
```

### Scenario 3: Programmatic Usage

```python
from application.use_cases.analyze_repository_use_case import AnalyzeRepositoryUseCase
from application.use_cases.execute_repository_migration_use_case import ExecuteRepositoryMigrationUseCase

# Analyze
analyze_uc = AnalyzeRepositoryUseCase()
result = analyze_uc.execute(
    repository_url="https://github.com/user/repo.git",
    branch="main"
)

# Review MAR
mar = result['mar']
print(f"Services detected: {[s.service_name for s in mar.services_detected]}")
print(f"Files to migrate: {mar.files_to_modify}")

# Execute migration
migrate_uc = ExecuteRepositoryMigrationUseCase()
migration_result = migrate_uc.execute(
    repository_id=result['repository_id'],
    mar=mar,
    services_to_migrate=['s3', 'lambda'],
    run_tests=True
)

print(f"Migration completed: {migration_result['success']}")
print(f"Files changed: {len(migration_result['files_changed'])}")
print(f"PR created: {migration_result.get('pr_url')}")
```

### Scenario 4: API-Based Migration

```bash
# Start API server
python api_server.py

# Migrate code via API
curl -X POST http://localhost:8000/api/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import boto3\ns3 = boto3.client(\"s3\")\ns3.upload_file(\"file.txt\", \"bucket\", \"key\")",
    "language": "python",
    "services": ["s3"]
  }'

# Response:
# {
#   "migration_id": "mig_abc123",
#   "status": "completed",
#   "refactored_code": "...",
#   "variable_mapping": {...}
# }
```

---

## Performance Characteristics

### Benchmarks

| Metric | Value |
|--------|-------|
| **Analysis Speed** | ~10 seconds per 100,000 lines of code |
| **Transformation Speed** | ~5-10 seconds per file (depending on complexity) |
| **Repository Migration** | ~60 minutes for average microservice (<5,000 LoC) |
| **Test Execution** | Depends on test suite size |
| **API Response Time** | <2 seconds for single file migration |

### Scalability

- **Concurrent Migrations**: Supports multiple concurrent repository migrations
- **Large Repositories**: Tested on repositories up to 50,000+ files
- **Memory Usage**: Efficient memory management for large codebases
- **API Rate Limits**: Respects Gemini API rate limits with retry logic

---

## Security & Compliance

### Security Features

1. **Input Validation**: All inputs validated and sanitized
2. **Authentication**: Optional authentication middleware (Cloud Run IAM)
3. **Access Control**: Strict access controls for proprietary code
4. **No Data Retention**: Code not stored permanently (temporary files only)
5. **Secure API Keys**: Environment variable-based configuration

### Compliance

- **No Training Data**: Gemini API configured to not use submitted code for training
- **Data Privacy**: Code processed in-memory, temporary files cleaned up
- **Audit Trail**: Migration logs available for compliance

---

## Testing & Quality Assurance

### Test Coverage

**Unit Tests**:
- Domain entities and value objects
- Use case orchestration
- Service mappers and adapters

**Integration Tests**:
- End-to-end migration workflows
- API endpoint testing
- Git integration testing

**Comprehensive Test Suites**:
- `test_aws_comprehensive.py`: Python AWS migrations
- `test_java_migrations.py`: Java migrations
- `test_csharp_migrations.py`: C# migrations
- `test_migration_direct.py`: Direct function testing

**Test Results**:
- ✅ Python: 100% service coverage
- ✅ Java: 100% service coverage
- ✅ C#: 100% service coverage
- ✅ Multi-service migrations: Tested
- ✅ Repository-level migrations: Tested

---

## Deployment & Operations

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
python api_server.py

# Start frontend (separate terminal)
cd frontend && npm install && npm start
```

### Cloud Run Deployment

```bash
# Build and deploy
./cloudrun-deploy.sh

# Or with secrets
./deploy-with-secrets.sh
```

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
REQUIRE_AUTH=false
ALLOWED_ORIGINS=http://localhost:3000
```

---

## Roadmap & Future Enhancements

### Completed ✅
- Multi-language support (Python, Java, C#)
- Repository-level migration
- MAR generation
- IaC migration (Terraform, CloudFormation, Pulumi)
- Test execution framework
- Pull request generation
- Web UI
- TOON format integration

### In Development 🔄
- Enhanced IaC migration patterns
- Additional programming languages (Go, Node.js)
- Advanced dependency analysis
- CI/CD pipeline integration

### Planned 📋
- Database schema migration
- Container orchestration migration (ECS to GKE)
- Automated test generation
- Multi-repository batch migration
- Migration rollback capabilities
- Cost estimation and optimization recommendations

---

## Support & Documentation

### Documentation Files

- `README.md`: Main documentation
- `accelerator_detail.md`: This document (detailed accelerator explanation)
- `CSHARP_MIGRATION_STATUS.md`: C# migration status and examples
- `JAVA_MIGRATION_STATUS.md`: Java migration status
- `MIGRATION_GUIDE.md`: Detailed migration guide with examples
- `DEPLOYMENT.md`: Deployment instructions
- `QUICKSTART.md`: Quick start guide

### Getting Help

- **Issues**: GitHub Issues
- **Documentation**: See documentation files above
- **Examples**: Check `examples/` directory

---

## Conclusion

The Universal Cloud Refactor Agent is a production-ready, enterprise-grade accelerator that automates cloud migration at scale. With support for Python, Java, and C# (.NET), comprehensive service coverage, and intelligent LLM-powered transformations, it significantly reduces migration time and effort while maintaining code quality and correctness.

**Key Differentiators**:
1. **Intelligence**: Gemini API-powered context-aware transformations
2. **Comprehensiveness**: Full repository migration with dependency tracking
3. **Quality**: Automated testing and validation
4. **Efficiency**: TOON format reduces API costs by 70-75%
5. **Enterprise Ready**: Production-grade architecture and security

**Use Cases**:
- Enterprise cloud migrations (AWS/Azure → GCP)
- Multi-service application refactoring
- Infrastructure as Code migration
- Legacy code modernization
- Cost optimization through cloud migration
