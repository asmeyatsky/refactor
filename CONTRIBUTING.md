# Contributing to Universal Cloud Refactor Agent

Thank you for your interest in contributing to the Universal Cloud Refactor Agent! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Node.js 18+ and npm (for frontend development)
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/asmeyatsky/refactor.git
   cd refactor
   ```

2. **Set up Python environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Set up frontend**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Development Workflow

### Code Style

- **Python**: Follow PEP 8 style guide. We use `black` for formatting and `flake8` for linting.
  ```bash
   black .
   flake8 .
   ```

- **JavaScript/React**: Follow ESLint rules. Run `npm run lint` in the frontend directory.

### Testing

- Run all tests:
  ```bash
   python -m pytest tests/
   ```

- Run specific test file:
  ```bash
   python -m pytest tests/domain/test_domain_entities.py
   ```

- Run with coverage:
  ```bash
   pytest --cov=. tests/
   ```

### Architecture

The project follows Clean/Hexagonal Architecture:

- **Domain Layer**: Business logic, entities, value objects, domain services
- **Application Layer**: Use cases that orchestrate domain logic
- **Infrastructure Layer**: Adapters and repositories implementing ports
- **Presentation Layer**: API endpoints and React frontend

When adding new features:
1. Define domain entities/value objects if needed
2. Create use cases in the application layer
3. Implement adapters in the infrastructure layer
4. Add API endpoints if needed
5. Update frontend if UI changes are required

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation updates

### Commit Messages

Follow conventional commits format:
- `feat: Add support for Azure Functions migration`
- `fix: Resolve AST transformation error`
- `docs: Update README with new examples`
- `test: Add tests for service mapper`

### Pull Request Process

1. Create a branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request with a clear description

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No breaking changes (or documented if intentional)
- [ ] Environment variables documented if added

## Adding New Service Mappings

To add support for a new cloud service migration:

1. **Add service enum** in `domain/value_objects/__init__.py`
2. **Create service mapping** in `infrastructure/adapters/service_mapping.py` or `azure_mapping.py`
3. **Add transformation logic** in `infrastructure/adapters/extended_semantic_engine.py`
4. **Add tests** in `tests/infrastructure/`
5. **Update documentation** in README.md

Example:
```python
# In service_mapping.py
AWSService.NEW_SERVICE: ServiceMigrationMapping(
    aws_service=AWSService.NEW_SERVICE,
    gcp_service=GCPService.EQUIVALENT,
    aws_sdk_imports=['boto3'],
    gcp_sdk_imports=['google.cloud.new_service'],
    # ... mapping details
)
```

## Adding LLM Provider Support

To add a new LLM provider:

1. Add provider initialization in `LLMProviderAdapter.__init__`
2. Implement `_generate_with_provider` method
3. Update `config.py` with provider configuration
4. Update `.env.example` with API key variable
5. Add to `requirements.txt` (optional dependencies)

## Debugging

### Enable Debug Logging

Set in `.env`:
```
LOG_LEVEL=DEBUG
```

### Run API Server Locally

```bash
python api_server.py
```

### Run Frontend Locally

```bash
cd frontend
npm start
```

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Be respectful and constructive in discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
