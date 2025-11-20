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

### Option 1: Repository-Level Migration 🆕

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

### Option 2: Command Line Interface (File/Codebase-Level)

```bash
# Migrate a codebase (auto-detect services)
python main.py /path/to/your/codebase --language python

# Migrate specific services
python main.py /path/to/your/codebase --language python --services s3 lambda dynamodb

# Verbose output
python main.py /path/to/your/codebase --language python --verbose
```

### Option 3: API Server

```bash
# Start the API server
python api_server.py

# Server runs on http://localhost:8000
# API docs available at http://localhost:8000/docs
```

### Option 4: Full Stack (API + Frontend)

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

### Option 5: Docker

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
from infrastructure.adapters.repository_migration import RepositoryMigrationEngine

# Initialize repository migration engine
migration_engine = RepositoryMigrationEngine()

# Step 1: Generate Migration Assessment Report (MAR)
mar_result = migration_engine.analyze_repository(
    repository_url="https://github.com/user/repo.git",
    branch="main"
)

print(f"Services detected: {mar_result['services_detected']}")
print(f"Files to modify: {mar_result['files_affected']}")
print(f"Confidence score: {mar_result['confidence_score']}")

# Step 2: Execute migration (if confidence is high)
if mar_result['confidence_score'] > 0.8:
    pr_result = migration_engine.migrate_repository(
        repository_url="https://github.com/user/repo.git",
        branch="main",
        migration_plan=mar_result
    )
    print(f"PR created: {pr_result['pr_url']}")
    print(f"Branch: {pr_result['branch_name']}")
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

# Migrate code
curl -X POST http://localhost:8000/api/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import boto3\ns3 = boto3.client(\"s3\")",
    "language": "python",
    "services": ["s3"]
  }'

# Check migration status
curl http://localhost:8000/api/migration/{migration_id}
```

## Configuration

### Environment Variables

Key variables in `.env`:

- `LLM_PROVIDER`: `mock`, `openai`, or `anthropic` (default: `mock`)
- `TEST_RUNNER`: `mock`, `pytest`, or `unittest` (default: `mock`)
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)

### Using Real LLM Providers

1. **OpenAI:**
   ```bash
   export LLM_PROVIDER=openai
   export OPENAI_API_KEY=your_key_here
   ```

2. **Anthropic:**
   ```bash
   export LLM_PROVIDER=anthropic
   export ANTHROPIC_API_KEY=your_key_here
   ```

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
