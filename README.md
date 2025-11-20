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
- **Repository-Level Migration** 🆕: Migrate entire codebases with a single command, including cross-file dependency tracking and atomic PR generation

## Supported Service Migrations

### AWS Services
- **S3 to Cloud Storage**: Object Storage
- **Lambda to Cloud Functions/Cloud Run**: Serverless Compute
- **DynamoDB to Firestore/Bigtable**: NoSQL Database
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

### Repository-Level Migration 🆕

Migrate entire Git repositories with a single command:

```python
from infrastructure.adapters.repository_migration import RepositoryMigrationEngine

# Initialize repository migration engine
migration_engine = RepositoryMigrationEngine()

# Migrate entire repository from Git URL
result = migration_engine.migrate_repository(
    repository_url="https://github.com/user/repo.git",
    branch="main",
    target_cloud="gcp",
    auto_approve=False  # Generate MAR first for review
)

# Review Migration Assessment Report (MAR)
print(f"Services detected: {result['mar']['services_detected']}")
print(f"Files to modify: {result['mar']['files_affected']}")
print(f"Estimated changes: {result['mar']['estimated_changes']}")

# Execute migration after review
if result['mar']['confidence_score'] > 0.8:
    pr_result = migration_engine.execute_migration(
        repository_url="https://github.com/user/repo.git",
        branch="main",
        migration_plan=result['mar']
    )
    print(f"PR created: {pr_result['pr_url']}")
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
# Migrate entire repository from Git URL
python main.py --repository https://github.com/user/repo.git --branch main

# Generate Migration Assessment Report (MAR) without executing
python main.py --repository https://github.com/user/repo.git --mar-only

# Migrate with specific services
python main.py --repository https://github.com/user/repo.git --services s3 lambda dynamodb

# Auto-approve and create PR
python main.py --repository https://github.com/user/repo.git --auto-approve
```

### File/Codebase-Level Migration

```bash
# Auto-detect and migrate all supported AWS services
python main.py /path/to/codebase --language python

# Migrate specific services only
python main.py /path/to/codebase --language python --services s3 lambda dynamodb

# Verbose output
python main.py /path/to/codebase --language python --verbose
```

## Testing

Run the complete test suite:

```bash
python -m unittest discover tests/
```

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

### In Development 🔄
- **Repository-Level Migration**: Migrate entire Git repositories with cross-file dependency tracking
- **Migration Assessment Report (MAR)**: Pre-migration analysis and planning
- **Atomic PR Generation**: Single Pull Request with all refactored changes
- **Git Integration**: Support for GitHub, GitLab, Bitbucket

### Planned Features 📋
- Infrastructure as Code (IaC) translation capabilities (CloudFormation to Terraform)
- Support for additional programming languages (Go, Node.js, C#)
- Container migration (ECS to GKE)
- Database schema migration capabilities
- CI/CD pipeline updates
- Cross-file dependency mapping and refactoring
- Automated test generation for refactored code

See [REPOSITORY_LEVEL_MIGRATION.md](REPOSITORY_LEVEL_MIGRATION.md) for detailed repository-level migration requirements.

## Contributing

We welcome contributions to the Cloud Refactor Agent. Please read our contribution guidelines for more information.

## License

This project is licensed under the MIT License.