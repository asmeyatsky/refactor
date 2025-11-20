# Repository-Level Migration Implementation Plan

## Overview

This document outlines the implementation plan for adding repository-level migration capabilities to the Universal Cloud Refactor Agent, as specified in the [Supplementary PRD](Supplementary%20PRD%20for%20code%20bases.pdf) and [REPOSITORY_LEVEL_MIGRATION.md](REPOSITORY_LEVEL_MIGRATION.md).

## Current State

### ✅ Existing Capabilities
- Individual file/snippet refactoring
- Multi-service migration within a single codebase
- AST-powered transformations
- Comprehensive service mappings (AWS & Azure to GCP)
- Test validation framework
- Web-based UI for file-level migrations

### 🔄 To Be Implemented
- Git repository integration (GitHub, GitLab, Bitbucket)
- Cross-file dependency mapping
- Migration Assessment Report (MAR) generation
- Atomic repository-wide refactoring
- Pull Request generation
- Infrastructure as Code (IaC) migration
- CI/CD pipeline updates

## Implementation Phases

### Phase 1: Git Integration & Repository Cloning (Weeks 1-2)

**Objectives:**
- Enable cloning repositories from Git providers
- Support GitHub, GitLab, and Bitbucket
- Basic repository structure analysis

**Tasks:**
1. **Create Git Adapter Infrastructure**
   - `infrastructure/adapters/git_adapter.py`
   - Support for GitHub API, GitLab API, Bitbucket API
   - SSH and HTTPS cloning support
   - Authentication handling (tokens, SSH keys)

2. **Repository Repository**
   - `infrastructure/repositories/repository_repository.py`
   - Store cloned repository metadata
   - Track repository state

3. **Dependencies**
   ```python
   # Add to requirements.txt
   GitPython>=3.1.40
   PyGithub>=2.1.1
   python-gitlab>=4.0.0
   atlassian-python-api>=3.41.0  # For Bitbucket
   ```

4. **Tests**
   - `tests/infrastructure/test_git_adapter.py`
   - Mock Git provider APIs
   - Test cloning and authentication

**Deliverables:**
- Git adapter supporting all three providers
- Repository cloning functionality
- Basic repository metadata extraction

### Phase 2: Codebase Indexing & Dependency Mapping (Weeks 3-4)

**Objectives:**
- Build dependency graph of the codebase
- Track cross-file references
- Identify imports/exports

**Tasks:**
1. **Dependency Graph Builder**
   - `infrastructure/adapters/dependency_graph_builder.py`
   - Parse imports/exports for Python and Java
   - Build graph structure
   - Track variable/constant dependencies

2. **Codebase Analyzer Enhancement**
   - Extend `infrastructure/adapters/code_analyzer.py`
   - Multi-file analysis
   - Cross-file service detection
   - Configuration file detection

3. **Domain Entities**
   - `domain/entities/repository.py` - Repository entity
   - `domain/entities/dependency_graph.py` - Dependency graph entity
   - `domain/value_objects/mar.py` - MAR value object

4. **Tests**
   - `tests/infrastructure/test_dependency_graph_builder.py`
   - Test with sample multi-file codebases

**Deliverables:**
- Dependency graph builder
- Cross-file reference tracking
- Import/export analysis

### Phase 3: Migration Assessment Report (MAR) Generation (Weeks 5-6)

**Objectives:**
- Generate comprehensive pre-migration analysis
- Estimate changes and complexity
- Provide confidence scores

**Tasks:**
1. **MAR Generator**
   - `infrastructure/adapters/mar_generator.py`
   - Analyze repository for cloud services
   - Estimate lines of change
   - Calculate confidence scores
   - Identify risks

2. **Use Cases**
   - `application/use_cases/analyze_repository_use_case.py`
   - `application/use_cases/generate_mar_use_case.py`

3. **MAR Format**
   - JSON schema for MAR
   - Markdown template for PR description
   - Export to various formats

4. **Tests**
   - `tests/application/test_mar_generation.py`
   - Test MAR generation with various repositories

**Deliverables:**
- MAR generation system
- Pre-migration analysis reports
- Confidence scoring algorithm

### Phase 4: Atomic Refactoring Engine (Weeks 7-8)

**Objectives:**
- Apply refactoring across entire repository
- Maintain consistency across files
- Handle cross-file dependencies

**Tasks:**
1. **Repository Refactoring Engine**
   - `infrastructure/adapters/repository_refactoring_engine.py`
   - Orchestrate multi-file transformations
   - Track changes across files
   - Ensure consistency

2. **Cross-File Dependency Handler**
   - `infrastructure/adapters/cross_file_dependency_handler.py`
   - Propagate variable/constant changes
   - Update imports/exports
   - Handle configuration changes

3. **Use Cases**
   - `application/use_cases/execute_repository_migration_use_case.py`

4. **Tests**
   - `tests/integration/test_repository_refactoring.py`
   - Test with real multi-file scenarios

**Deliverables:**
- Atomic refactoring engine
- Cross-file dependency handling
- Consistency validation

### Phase 5: Infrastructure as Code (IaC) Migration (Weeks 9-10)

**Objectives:**
- Detect and update IaC files
- Update CI/CD pipelines
- Handle configuration files

**Tasks:**
1. **IaC Detector**
   - `infrastructure/adapters/iac_detector.py`
   - Detect Terraform, CloudFormation, Pulumi files
   - Parse configuration files

2. **IaC Migrator**
   - `infrastructure/adapters/iac_migrator.py`
   - Transform Terraform configurations
   - Update CloudFormation templates
   - Modify CI/CD pipeline files

3. **Configuration File Handler**
   - `infrastructure/adapters/config_file_handler.py`
   - Update YAML, JSON configs
   - Handle environment variable files

4. **Tests**
   - `tests/infrastructure/test_iac_migration.py`

**Deliverables:**
- IaC detection and migration
- CI/CD pipeline updates
- Configuration file handling

### Phase 6: PR Generation & Test Integration (Weeks 11-12)

**Objectives:**
- Generate Pull Requests with all changes
- Execute tests post-migration
- Generate test reports

**Tasks:**
1. **PR Manager**
   - `infrastructure/adapters/pr_manager.py`
   - Create branches
   - Commit changes
   - Open Pull Requests
   - Generate PR descriptions from MAR

2. **Test Execution Framework**
   - `infrastructure/adapters/test_execution_framework.py`
   - Execute test commands (pytest, npm test, etc.)
   - Parse test results
   - Generate test reports

3. **Test Generator** (Optional)
   - `infrastructure/adapters/test_generator.py`
   - Generate basic tests for critical functions
   - Focus on cloud service interactions

4. **Use Cases**
   - `application/use_cases/create_pr_use_case.py`
   - `application/use_cases/execute_tests_use_case.py`

5. **Tests**
   - `tests/integration/test_pr_generation.py`
   - `tests/integration/test_test_execution.py`

**Deliverables:**
- PR generation system
- Test execution framework
- Test reporting

## Technical Architecture

### New Components

```
Application Layer
├── Use Cases
│   ├── AnalyzeRepositoryUseCase
│   ├── GenerateMARUseCase
│   ├── ExecuteRepositoryMigrationUseCase
│   ├── CreatePRUseCase
│   └── ExecuteTestsUseCase

Infrastructure Layer
├── Adapters
│   ├── GitAdapter (GitHub, GitLab, Bitbucket)
│   ├── DependencyGraphBuilder
│   ├── MARGenerator
│   ├── RepositoryRefactoringEngine
│   ├── CrossFileDependencyHandler
│   ├── IACDetector
│   ├── IACMigrator
│   ├── ConfigFileHandler
│   ├── PRManager
│   └── TestExecutionFramework
└── Repositories
    └── RepositoryRepositoryAdapter

Domain Layer
├── Entities
│   ├── Repository
│   └── DependencyGraph
└── Value Objects
    └── MigrationAssessmentReport (MAR)
```

### Integration Points

1. **Existing Refactoring Engine**: Repository-level refactoring will use existing `ExtendedSemanticRefactoringService` and `AzureExtendedSemanticRefactoringService`

2. **Service Mappings**: Leverage existing service mapping infrastructure

3. **AST Transformations**: Use existing AST transformation engines

4. **Verification**: Integrate with existing verification framework

## Dependencies

### New Python Packages

```python
# Git operations
GitPython>=3.1.40

# Git provider APIs
PyGithub>=2.1.1          # GitHub
python-gitlab>=4.0.0     # GitLab
atlassian-python-api>=3.41.0  # Bitbucket

# Dependency analysis
networkx>=3.2            # For dependency graphs
astunparse>=1.6.3        # For AST to code conversion

# IaC parsing
pyyaml>=6.0.1            # YAML parsing
hcl2>=0.3.0              # Terraform parsing
```

### Configuration

Add to `.env.example`:
```bash
# Git Provider Credentials
GITHUB_TOKEN=
GITLAB_TOKEN=
BITBUCKET_USERNAME=
BITBUCKET_APP_PASSWORD=

# Repository Migration Settings
REPOSITORY_MIGRATION_TIMEOUT=1800  # 30 minutes
MAX_REPOSITORY_SIZE=50000          # Lines of code
MAR_CONFIDENCE_THRESHOLD=0.8
```

## API Endpoints (New)

```python
# Repository Analysis
POST /api/repository/analyze
GET /api/repository/{repo_id}/mar

# Repository Migration
POST /api/repository/migrate
GET /api/repository/{repo_id}/status

# PR Management
POST /api/repository/{repo_id}/create-pr
GET /api/repository/{repo_id}/pr
```

## Testing Strategy

### Unit Tests
- Git adapter functionality
- Dependency graph building
- MAR generation
- Cross-file dependency handling

### Integration Tests
- End-to-end repository migration
- PR creation workflow
- Test execution framework

### E2E Tests
- Full repository migration with real Git repositories (test repos)
- MAR generation and review workflow
- PR creation and validation

## Security Considerations

1. **Credential Management**
   - Never store credentials in code
   - Use environment variables or secure vaults
   - Implement credential rotation

2. **Repository Access**
   - Least-privilege access tokens
   - Read-only access when possible
   - Temporary credentials for operations

3. **Code Handling**
   - Process code in isolated environments
   - Clean up cloned repositories after processing
   - No persistent storage of user code

## Performance Targets

- **Repository Analysis**: < 5 minutes for 20K LoC
- **MAR Generation**: < 2 minutes for 20K LoC
- **Refactoring Execution**: < 20 minutes for 20K LoC
- **Total Process**: < 30 minutes for 20K LoC

## Success Metrics

- **MAR Accuracy**: >90% accurate service detection
- **Migration Success**: >85% of migrations complete successfully
- **Test Pass Rate**: >90% of migrations maintain test pass rate
- **PR Quality**: >80% of PRs require minimal manual changes

## Risk Mitigation

1. **Large Repositories**: Implement chunking and incremental processing
2. **Complex Dependencies**: Use conservative approach, flag for manual review
3. **Test Failures**: Provide detailed failure reports and rollback options
4. **API Rate Limits**: Implement retry logic and rate limit handling

## Documentation Updates

- [x] README.md - Updated with repository-level features
- [x] QUICKSTART.md - Added repository migration examples
- [x] CONTRIBUTING.md - Added repository-level contribution guidelines
- [x] UNIVERSAL_CLOUD_REFACTOR_AGENT_PRD.md - Added repository-level requirements
- [x] REPOSITORY_LEVEL_MIGRATION.md - Created comprehensive requirements doc
- [x] REPOSITORY_MIGRATION_IMPLEMENTATION_PLAN.md - This document

## Next Steps

1. **Review and Approve**: Review this implementation plan with stakeholders
2. **Set Up Development Environment**: Install new dependencies
3. **Create Feature Branch**: `feature/repository-level-migration`
4. **Begin Phase 1**: Start with Git integration
5. **Iterative Development**: Follow phases sequentially with regular reviews

## Open Questions

1. **Multi-Language Support**: How to handle repositories with multiple languages?
   - *Proposed*: Process each language sequentially, single PR

2. **Large Repository Handling**: What's the maximum repository size?
   - *Proposed*: 50K LoC initially, with chunking for larger repos

3. **Rollback Strategy**: How detailed should rollback be?
   - *Proposed*: Branch-based rollback (delete branch/close PR)

4. **MAR Review Process**: Should MAR require manual approval?
   - *Proposed*: Yes, with auto-approve option for high-confidence migrations

---

**Status**: Planning Complete, Ready for Implementation  
**Last Updated**: 2025-01-XX  
**Next Review**: After Phase 1 completion
