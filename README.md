# Universal Cloud Refactor Agent

The Universal Cloud Refactor Agent is an autonomous system designed to automate the complex conversion of proprietary cloud APIs and configurations, targeting platform transitions such as migrating AWS/Azure SDK usage to Google Cloud Platform (GCP) SDK usage at enterprise scale.

## Features

- **Multi-Agent Architecture**: Implements Planner, Refactoring Engine, and Verification agents
- **AST-Powered Transformations**: Uses Abstract Syntax Trees for reliable code transformations
- **Multi-Cloud Migration Support**: Migrates AWS and Azure services to GCP equivalents
- **Auto-Detection**: Automatically detects AWS/Azure services in code and suggests migrations
- **Comprehensive Verification**: Ensures behavioral preservation through testing
- **Security Validation**: Implements mandatory security checks
- **Context Management**: Stores and manages information between refactoring tasks
- **Repository-Level Migration** 🆕: Migrate entire Git repositories with cross-file dependency tracking, atomic PR generation, and Migration Assessment Reports (MAR)
- **Agentic Web UI** 🆕: Step-by-step wizard interface for guided migration workflows
- **TOON Format Integration** 🆕: Token-optimized data format reducing Gemini API costs by 70-75%
- **Infrastructure as Code Migration** 🆕: Automatic detection and migration of Terraform, CloudFormation, and Pulumi files
- **Test Execution Framework** 🆕: Automated test execution after migration with multi-framework support

## Supported Service Migrations

### AWS Services
- **S3 to Cloud Storage**: Object Storage
- **Lambda to Cloud Functions/Cloud Run**: Serverless Compute
- **DynamoDB to Firestore/Bigtable**: NoSQL Database
  - **Smart Migration Detection**: Automatically detects migration scripts (reads from DynamoDB, writes to Firestore) and preserves boto3 for reading operations
  - **Application Code Migration**: Fully converts DynamoDB code to Firestore for application code
- **SQS to Pub/Sub**: Message Queuing
- **SNS to Pub/Sub**: Notification Service
- **RDS to Cloud SQL**: Relational Database
- **EC2 to Compute Engine**: Virtual Machines
- **CloudWatch to Cloud Monitoring**: Monitoring and Logging
- **API Gateway to Apigee X**: API Management
- **ElastiCache to Memorystore**: In-Memory Caching
- **EKS to GKE**: Container Orchestration
- **Fargate to Cloud Run**: Serverless Container Computing

### Azure Services
- **Blob Storage to Cloud Storage**: Object Storage
- **Functions to Cloud Functions**: Serverless Compute
- **Cosmos DB to Firestore**: NoSQL Database
- **Service Bus to Pub/Sub**: Messaging Service
- **Event Hubs to Pub/Sub**: Event Streaming
- **SQL Database to Cloud SQL**: Relational Database
- **Virtual Machines to Compute Engine**: Virtual Machines
- **Monitor to Cloud Monitoring**: Monitoring and Logging
- **API Management to Apigee**: API Management
- **Redis Cache to Memorystore**: In-Memory Caching
- **AKS to GKE**: Container Orchestration
- **Container Instances to Cloud Run**: Container Service
- **App Service to Cloud Run**: Web Application Hosting

## Architecture

The system follows clean/hexagonal architecture principles:

```
Domain Layer
├── Entities: Codebase, RefactoringPlan
├── Value Objects: MigrationType, RefactoringResult
├── Services: RefactoringDomainService
└── Ports: Interfaces for external dependencies

Application Layer
└── Use Cases: AnalyzeCodebase, CreateMultiServiceRefactoringPlan, ExecuteMultiServiceRefactoringPlan

Infrastructure Layer
├── Repositories: Codebase, Plan, File storage
├── Adapters: Code analysis, LLM, AST, Testing, Service Mapping
└── Config: Dependency injection

Presentation Layer
├── API: REST endpoints for web and programmatic access
└── UI: React-based web interface
```

## Automatic Git Hooks

This repository includes a post-commit hook that automatically pushes changes to the remote repository when committing to the main branch.

## Installation

```bash
# The system requires Python 3.7+
pip install astor  # For AST transformations
```

## Usage

### Web Interface 🆕 (Recommended)

Start the agentic web interface for guided migration:

```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Start frontend
cd frontend && npm start
```

Visit http://localhost:3000 for the step-by-step migration wizard:
1. **Select Cloud Provider** (AWS or Azure)
2. **Choose Input Method** (Code Snippet or Repository)
3. **Provide Code/Repository** (paste code or import Git repo)
4. **Review & Migrate** (see results and create PR)

### Repository-Level Migration 🆕

Migrate entire Git repositories via CLI:

```bash
# Analyze repository and generate MAR
python main.py repo analyze https://github.com/user/repo.git --branch main --token YOUR_TOKEN

# Execute migration
python main.py repo migrate <repository_id> --create-pr --run-tests

# List analyzed repositories
python main.py repo list
```

Or programmatically:

```python
from application.use_cases.analyze_repository_use_case import AnalyzeRepositoryUseCase
from application.use_cases.execute_repository_migration_use_case import ExecuteRepositoryMigrationUseCase

# Analyze repository
analyze_uc = AnalyzeRepositoryUseCase()
result = analyze_uc.execute(
    repository_url="https://github.com/user/repo.git",
    branch="main"
)

# Execute migration
migrate_uc = ExecuteRepositoryMigrationUseCase()
migration_result = migrate_uc.execute(
    repository_id=result['repository_id'],
    mar=result['mar'],
    run_tests=True
)
```

### Multi-Service Migration

```python
from cloud_refactor_agent.infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
from domain.entities.codebase import ProgrammingLanguage

# Create the multi-service migration system
orchestrator = create_multi_service_migration_system()

# Execute a migration with auto-detection
result = orchestrator.execute_migration(
    codebase_path="/path/to/your/codebase",
    language=ProgrammingLanguage.PYTHON
)

print(f"Migration completed: {result['migration_id']}")
print(f"Success: {result['verification_result']['success']}")
print(f"Services migrated: {result['services_migrated']}")

# Or migrate specific services
result = orchestrator.execute_migration(
    codebase_path="/path/to/your/codebase",
    language=ProgrammingLanguage.PYTHON,
    services_to_migrate=["s3", "lambda", "dynamodb"]
)
```

### Using Individual Components

```python
# Initialize a codebase
from application.use_cases import InitializeCodebaseUseCase
from infrastructure.repositories import CodebaseRepositoryAdapter
from infrastructure.adapters import CodeAnalyzerAdapter

init_use_case = InitializeCodebaseUseCase(
    codebase_repo=CodebaseRepositoryAdapter(),
    code_analyzer=CodeAnalyzerAdapter()
)

codebase = init_use_case.execute("/path/to/codebase", ProgrammingLanguage.PYTHON)

# Analyze the codebase for all AWS service usage
from application.use_cases import AnalyzeCodebaseUseCase
analyze_use_case = AnalyzeCodebaseUseCase(
    code_analyzer=CodeAnalyzerAdapter(),
    codebase_repo=CodebaseRepositoryAdapter()
)

analysis_report = analyze_use_case.execute(codebase.id)
print(f"AWS services found: {analysis_report['aws_services_found']}")
```

## Command Line Usage

### Repository-Level Migration 🆕

```bash
# Analyze repository and generate MAR
python main.py repo analyze https://github.com/user/repo.git \
  --branch main \
  --token YOUR_GITHUB_TOKEN \
  --output mar.json

# Execute migration with PR creation
python main.py repo migrate <repository_id> \
  --services s3 lambda \
  --create-pr \
  --run-tests \
  --branch-name cloud-migration-2024

# List all analyzed repositories
python main.py repo list
```

### File/Codebase-Level Migration

```bash
# Auto-detect and migrate all supported services
python main.py local /path/to/codebase --language python

# Migrate specific services only
python main.py local /path/to/codebase \
  --language python \
  --services s3 lambda dynamodb \
  --verbose
```

## Testing

### Comprehensive Test Suites

The project includes comprehensive test suites for all AWS services:

**API-Based Testing:**
```bash
# Start API server first
python3 api_server.py

# Run comprehensive AWS tests (Python and Java)
python3 test_aws_comprehensive.py
```

**Direct Function Testing:**
```bash
# Test migration functions directly (no API server required)
python3 test_migration_direct.py
```

**Test Coverage:**
- ✅ S3 (basic operations, presigned URLs)
- ✅ Lambda (handlers, S3 integration)
- ✅ DynamoDB (basic operations, migration scripts)
- ✅ SQS (send/receive messages)
- ✅ SNS (publish messages)
- ✅ Multi-service migrations
- ✅ Java code migrations (uses Gemini API for intelligent transformations)

**Unit Tests:**
```bash
python -m unittest discover tests/
```

### DynamoDB Migration Script Detection

The tool automatically detects migration scripts vs application code:

- **Migration Scripts**: Preserves boto3 for reading from DynamoDB, converts writes to Firestore
- **Application Code**: Fully converts all DynamoDB code to Firestore

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed examples.

## Design Decisions

### Multi-Agent Architecture

The system implements specialized agents:
- **Planner Agent**: Handles analysis, multi-service planning, and task decomposition
- **Refactoring Engine**: Executes transformations using LLM-generated recipes for multiple services
- **Verification Agent**: Ensures quality, correctness, and security across all migrated services

### Service Mapping Framework

The system includes a comprehensive service mapping framework that defines how each AWS service maps to its GCP equivalent, including:
- API call transformations
- Authentication method translations
- Configuration parameter mappings
- Data model adaptations

### Extended AST Transformations

The system uses Abstract Syntax Tree (AST) manipulation for reliable code transformations across multiple service types, preserving code structure while updating cloud-specific calls.

### Verification and Security

A mandatory verification gate runs tests to ensure behavior preservation across all migrated services, with security checks validating the refactored code for vulnerabilities.

## Performance

The system is designed to:
- Complete analysis within 10 seconds per 100,000 lines of code
- Process an average-sized microservice (<5,000 LoC) within 60 minutes
- Maintain 100% test pass rate after refactoring
- Achieve >70% reduction in resource hours compared to manual migration

## Security

- Proprietary code handling with strict access controls
- Input validation and sanitization
- Mandatory review policy before execution
- No use of third-party LLM APIs that train on submitted data

## Roadmap

### Current Capabilities ✅
- Individual file/snippet refactoring
- Multi-service migration within codebase
- Comprehensive AWS & Azure to GCP service mappings
- AST-powered transformations
- Test validation framework
- **Repository-Level Migration**: Full Git repository migration with MAR generation
- **Agentic Web UI**: Step-by-step wizard interface
- **TOON Format Integration**: 70-75% token reduction for Gemini API calls
- **Infrastructure as Code Migration**: Terraform, CloudFormation, Pulumi support
- **Test Execution Framework**: Automated testing with pytest, unittest, Jest, JUnit
- **Pull Request Generation**: Automatic PR/MR creation for GitHub, GitLab, Bitbucket

### In Development 🔄
- Enhanced IaC migration patterns
- Additional programming language support (Go, Node.js, C#)
- Advanced dependency analysis
- CI/CD pipeline integration

### Planned Features 📋
- Database schema migration capabilities
- Container orchestration migration (ECS to GKE)
- Automated test generation for refactored code
- Multi-repository batch migration
- Migration rollback capabilities

See [REPOSITORY_LEVEL_MIGRATION.md](REPOSITORY_LEVEL_MIGRATION.md) for detailed repository-level migration requirements.

## Contributing

We welcome contributions to the Cloud Refactor Agent. Please read our contribution guidelines for more information.

## License

This project is licensed under the MIT License.