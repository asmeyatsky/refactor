# Quick Start Guide

Get up and running with the Universal Cloud Refactor Agent in minutes!

## Prerequisites

- Python 3.7+
- Node.js 18+ (for frontend)
- pip and npm

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/asmeyatsky/refactor.git
cd refactor
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (optional - defaults work for testing)
```

### 4. Install Frontend Dependencies (Optional)

```bash
cd frontend
npm install
cd ..
```

## Running the Application

### Option 1: Agentic Web Interface 🆕 (Recommended)

The new step-by-step wizard guides you through migration:

**Terminal 1 - Start API Server:**
```bash
python api_server.py
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm start
```

Visit http://localhost:3000 and follow the wizard:
1. Select your cloud provider (AWS or Azure)
2. Choose input method (Code Snippet or Repository)
3. Provide your code or repository URL
4. Review results and create Pull Request

### Option 2: Repository-Level Migration via CLI 🆕

```bash
# Analyze repository and generate MAR
python main.py repo analyze https://github.com/user/repo.git \
  --branch main \
  --token YOUR_TOKEN \
  --output mar.json

# Execute migration with PR creation
python main.py repo migrate <repository_id> \
  --create-pr \
  --run-tests \
  --branch-name cloud-migration

# List analyzed repositories
python main.py repo list
```

### Option 3: Command Line Interface (File/Codebase-Level)

```bash
# Migrate a codebase (auto-detect services)
python main.py /path/to/your/codebase --language python

# Migrate specific services
python main.py /path/to/your/codebase --language python --services s3 lambda dynamodb

# Verbose output
python main.py /path/to/your/codebase --language python --verbose
```

### Option 4: API Server

```bash
# Start the API server
python api_server.py

# Server runs on http://localhost:8000
# API docs available at http://localhost:8000/docs
```

### Option 5: Full Stack (API + Frontend)

**Terminal 1 - API Server:**
```bash
python api_server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

Visit http://localhost:3000 to use the web interface.

### Option 6: Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# API: http://localhost:8000
# Frontend: http://localhost:3000
```

## Testing

### Run Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
pytest --cov=. tests/

# Run specific test file
python -m pytest tests/domain/test_domain_entities.py
```

### Test the CLI

```bash
# Create a test file
mkdir test_codebase
echo "import boto3
s3 = boto3.client('s3')
s3.upload_file('test.txt', 'my-bucket', 'test.txt')" > test_codebase/test.py

# Run migration
python main.py test_codebase --language python --services s3
```

## Example Usage

### Repository-Level Migration Example 🆕

```python
from application.use_cases.analyze_repository_use_case import AnalyzeRepositoryUseCase
from application.use_cases.execute_repository_migration_use_case import ExecuteRepositoryMigrationUseCase
from infrastructure.adapters.git_adapter import GitCredentials, GitProvider

# Step 1: Analyze repository
analyze_uc = AnalyzeRepositoryUseCase()
result = analyze_uc.execute(
    repository_url="https://github.com/user/repo.git",
    branch="main",
    credentials=GitCredentials(
        provider=GitProvider.GITHUB,
        token="your_token_here"
    )
)

print(f"Repository ID: {result['repository_id']}")
print(f"Services detected: {len(result['mar'].services_detected)}")
print(f"Files to modify: {result['mar'].files_to_modify_count}")
print(f"Confidence: {result['mar'].confidence_score:.1%}")

# Step 2: Execute migration
migrate_uc = ExecuteRepositoryMigrationUseCase()
migration_result = migrate_uc.execute(
    repository_id=result['repository_id'],
    mar=result['mar'],
    services_to_migrate=['s3', 'lambda'],  # Optional: specific services
    run_tests=True
)

print(f"Files changed: {migration_result['total_files_changed']}")
print(f"Test results: {migration_result.get('test_results')}")
```

### File/Codebase-Level Migration Example

```python
from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
from domain.entities.codebase import ProgrammingLanguage

# Create migration system
orchestrator = create_multi_service_migration_system()

# Execute migration
result = orchestrator.execute_migration(
    codebase_path="/path/to/codebase",
    language=ProgrammingLanguage.PYTHON,
    services_to_migrate=["s3", "lambda"]  # Optional: auto-detect if None
)

print(f"Migration ID: {result['migration_id']}")
print(f"Success: {result['verification_result']['success']}")
```

### API Example

```bash
# Get supported services
curl http://localhost:8000/api/services

# Migrate code snippet
curl -X POST http://localhost:8000/api/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import boto3\ns3 = boto3.client(\"s3\")",
    "language": "python",
    "services": ["s3"],
    "cloud_provider": "aws"
  }'

# Analyze repository
curl -X POST http://localhost:8000/api/repository/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/user/repo.git",
    "branch": "main",
    "token": "your_token"
  }'

# Execute repository migration
curl -X POST http://localhost:8000/api/repository/{repository_id}/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["s3", "lambda"],
    "create_pr": true,
    "run_tests": true
  }'

# Check migration status
curl http://localhost:8000/api/migration/{migration_id}
```

## Configuration

### Environment Variables

Key variables in `.env`:

- `LLM_PROVIDER`: `gemini` (default: `mock`)
- `GEMINI_API_KEY`: Your Google Gemini API key (required for LLM features)
- `TEST_RUNNER`: `mock`, `pytest`, or `unittest` (default: `mock`)
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

### Using Gemini LLM Provider

```bash
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=your_gemini_api_key_here
```

**Note**: The system uses TOON format automatically to optimize token usage, reducing Gemini API costs by 70-75%.

### Using Real Test Runner

```bash
export TEST_RUNNER=pytest
# or
export TEST_RUNNER=unittest
```

## Troubleshooting

### Import Errors

```bash
# Make sure you're in the project root
pwd  # Should show /path/to/refactor

# Install in development mode
pip install -e .
```

### Port Already in Use

```bash
# Change port in .env
API_PORT=8001

# Or kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Frontend Not Connecting to API

Check `REACT_APP_API_BASE_URL` in `.env` matches your API server URL.

## Next Steps

- Read the [README.md](README.md) for detailed documentation
- Check [REPOSITORY_LEVEL_MIGRATION.md](REPOSITORY_LEVEL_MIGRATION.md) for repository-level migration capabilities
- Review [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- Review [COMPLETENESS_REPORT.md](COMPLETENESS_REPORT.md) for architecture details

## Support

- Open an issue on GitHub
- Check existing issues for solutions
- Review documentation in `/docs`

Happy migrating! 🚀
