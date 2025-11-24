"""
FastAPI server for the Cloud Refactor Agent
Provides API endpoints for the frontend application
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import asyncio
import threading
from pathlib import Path
import tempfile
import os

from domain.entities.codebase import ProgrammingLanguage
from application.use_cases import (
    InitializeCodebaseUseCase,
    CreateMultiServiceRefactoringPlanUseCase,
    ExecuteMultiServiceRefactoringPlanUseCase
)
from application.use_cases.analyze_repository_use_case import AnalyzeRepositoryUseCase
from application.use_cases.execute_repository_migration_use_case import ExecuteRepositoryMigrationUseCase
from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
from infrastructure.adapters.git_adapter import GitCredentials, GitProvider
from domain.value_objects import AWSService, AzureService, GCPService

app = FastAPI(
    title="Cloud Refactor Agent API",
    description="API for cloud service refactoring and migration",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for migration jobs (in production, use a database)
migration_jobs = {}

# Progress tracking for jobs
job_progress = {}

class MigrateRequest(BaseModel):
    code: str
    language: str
    services: List[str]
    cloud_provider: Optional[str] = None  # 'aws' or 'azure'


class MigrateResponse(BaseModel):
    migration_id: str
    status: str
    message: str
    created_at: datetime


@app.get("/")
def read_root():
    return {"message": "Cloud Refactor Agent API", "status": "running"}


@app.get("/api/services")
def get_supported_services():
    """Get list of supported cloud services for migration"""
    aws_services = [service.value for service in AWSService]
    azure_services = [service.value for service in AzureService]
    gcp_services = [service.value for service in GCPService]
    
    return {
        "aws_services": aws_services,
        "azure_services": azure_services,
        "gcp_services": gcp_services
    }


@app.post("/api/migrate", response_model=MigrateResponse)
async def migrate_code(request: MigrateRequest, background_tasks: BackgroundTasks):
    """Initiate a code migration process"""
    migration_id = f"mig_{uuid4().hex[:8]}"
    
    # Validate input
    if request.language not in ["python", "java"]:
        raise HTTPException(status_code=400, detail="Unsupported language")
    
    if not request.services:
        raise HTTPException(status_code=400, detail="At least one service must be selected")
    
    # Create a temporary file with the provided code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(request.code)
        temp_file_path = temp_file.name
    
    # Store job info
    migration_jobs[migration_id] = {
        "status": "pending",
        "request": request,
        "temp_file_path": temp_file_path,
        "created_at": datetime.now(),
        "result": None
    }
    
    # Initialize progress tracking
    job_progress[migration_id] = {
        "refactoring": {"progress": 0.0, "message": "Initializing..."},
        "validation": {"progress": 0.0, "message": "Waiting..."}
    }
    
    # Start migration in background
    background_tasks.add_task(execute_migration, migration_id, request, temp_file_path)
    
    return MigrateResponse(
        migration_id=migration_id,
        status="pending",
        message="Migration started",
        created_at=datetime.now()
    )


@app.get("/api/migration/{migration_id}")
def get_migration_status(migration_id: str):
    """Get the status of a migration job (supports both code snippet and repository migrations)"""
    job = migration_jobs.get(migration_id)
    if not job:
        raise HTTPException(status_code=404, detail="Migration job not found")
    
    response = {
        "migration_id": migration_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "result": job["result"],
        "progress": job_progress.get(migration_id, {
            "refactoring": {"progress": 0.0, "message": "Initializing..."},
            "validation": {"progress": 0.0, "message": "Waiting..."}
        })
    }
    
    # Handle code snippet migrations
    if "request" in job and hasattr(job["request"], "code"):
        response["code"] = job["request"].code  # Include original code for reference
        
        # If migration completed, include refactored code and variable mapping if available
        if job["status"] == "completed" and job["result"]:
            result = job["result"]
            if isinstance(result, dict):
                # Try to extract refactored code from result - prioritize top level
                if "refactored_code" in result:
                    response["refactored_code"] = result["refactored_code"]
                elif "execution_result" in result and isinstance(result["execution_result"], dict):
                    if "refactored_code" in result["execution_result"]:
                        response["refactored_code"] = result["execution_result"]["refactored_code"]
                elif "transformed_files" in result:
                    # If we have transformed files info, try to read the refactored code
                    try:
                        temp_file_path = job.get("temp_file_path", "")
                        if temp_file_path:
                            temp_dir = Path(temp_file_path).parent
                            codebase_path = temp_dir / "codebase"
                            lang_ext_map = {'python': 'py', 'java': 'java'}
                            file_ext = lang_ext_map.get(job['request'].language, 'py')
                            code_file = codebase_path / f"code.{file_ext}"
                            if code_file.exists():
                                with open(code_file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # CRITICAL: Final AWS cleanup pass before returning
                                    if job['request'].language == 'python':
                                        from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
                                        ast_engine = ExtendedASTTransformationEngine()
                                        if hasattr(ast_engine, '_aggressive_aws_cleanup'):
                                            content = ast_engine._aggressive_aws_cleanup(content)
                                    response["refactored_code"] = content
                    except Exception as e:
                        print(f"Warning: Could not read refactored code from file: {e}")
                
                # Extract variable mapping if available - prioritize top level
                if "variable_mapping" in result:
                    response["variable_mapping"] = result["variable_mapping"]
                elif "execution_result" in result and isinstance(result["execution_result"], dict):
                    if "variable_mapping" in result["execution_result"]:
                        response["variable_mapping"] = result["execution_result"]["variable_mapping"]
                
                # Also include success flag if available
                if "success" in result:
                    response["success"] = result["success"]
                else:
                    response["success"] = True  # If completed, assume success unless error present
    
    # Handle repository migrations
    elif "repository_id" in job:
        response["repository_id"] = job["repository_id"]
        
        # If migration completed, include all repository migration results
        if job["status"] == "completed" and job["result"]:
            result = job["result"]
            if isinstance(result, dict):
                # Include all repository migration fields
                response.update({
                    "success": result.get("success", True),
                    "files_changed": result.get("files_changed", []),
                    "files_failed": result.get("files_failed", []),
                    "total_files_changed": result.get("total_files_changed", 0),
                    "total_files_failed": result.get("total_files_failed", 0),
                    "test_results": result.get("test_results"),
                    "pr_url": result.get("pr_url"),
                    "refactored_files": result.get("refactored_files", {}),
                    "error": result.get("error")
                })
        elif job["status"] == "failed" and job["result"]:
            result = job["result"]
            if isinstance(result, dict):
                response["error"] = result.get("error", "Migration failed")
                response["success"] = False
    
    return response


def execute_migration(migration_id: str, request: MigrateRequest, temp_file_path: str):
    """Execute the migration in the background with progress tracking"""
    try:
        # Update status to in progress
        migration_jobs[migration_id]["status"] = "in_progress"
        
        # Update progress
        def update_refactoring_progress(message: str, progress: float):
            if migration_id in job_progress:
                job_progress[migration_id]["refactoring"] = {
                    "progress": progress,
                    "message": message
                }
        
        def update_validation_progress(message: str, progress: float):
            if migration_id in job_progress:
                job_progress[migration_id]["validation"] = {
                    "progress": progress,
                    "message": message
                }
        
        update_refactoring_progress("Starting refactoring...", 5.0)
        
        # Map language string to enum
        language_map = {
            'python': ProgrammingLanguage.PYTHON,
            'java': ProgrammingLanguage.JAVA
        }
        language = language_map.get(request.language)
        
        if not language:
            raise ValueError(f"Unsupported language: {request.language}")
        
        # Create temporary directory structure
        temp_dir = Path(temp_file_path).parent
        codebase_path = temp_dir / "codebase"
        codebase_path.mkdir(exist_ok=True)
        
        # Copy the uploaded file to the codebase directory
        import shutil
        # Map language to file extension
        lang_ext_map = {'python': 'py', 'java': 'java'}
        file_ext = lang_ext_map.get(request.language, 'py')
        target_file = codebase_path / f"code.{file_ext}"
        shutil.copy2(temp_file_path, target_file)
        
        # Create orchestrator and execute migration
        update_refactoring_progress("Creating migration orchestrator...", 10.0)
        orchestrator = create_multi_service_migration_system()
        
        update_refactoring_progress(f"Refactoring {len(request.services)} service(s)...", 20.0)
        result = orchestrator.execute_migration(
            str(codebase_path),
            language,
            services_to_migrate=request.services
        )
        update_refactoring_progress("Refactoring complete", 90.0)
        
        # Read the refactored code from the file AFTER transformation completes
        refactored_code = None
        # Map language to file extension
        lang_ext_map = {'python': 'py', 'java': 'java'}
        file_ext = lang_ext_map.get(request.language, 'py')
        code_file = codebase_path / f"code.{file_ext}"
        
        try:
            if code_file.exists():
                with open(code_file, 'r', encoding='utf-8') as f:
                    refactored_code = f.read()
                    
                    # CRITICAL: Final AWS cleanup pass before returning
                    if request.language == 'python':
                        from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
                        ast_engine = ExtendedASTTransformationEngine()
                        if hasattr(ast_engine, '_aggressive_aws_cleanup'):
                            refactored_code = ast_engine._aggressive_aws_cleanup(refactored_code)
        except Exception as e:
            print(f"Warning: Could not read refactored code: {e}")
        
        # Add refactored code to result
        if refactored_code:
            result["refactored_code"] = refactored_code
        else:
            # Fallback to original code if transformation didn't happen or file can't be read
            result["refactored_code"] = request.code
        
        # Validate the refactored code
        update_refactoring_progress("Refactoring complete", 100.0)
        update_validation_progress("Starting validation...", 0.0)
        
        from application.use_cases.validate_gcp_code_use_case import ValidateGCPCodeUseCase
        
        validator = ValidateGCPCodeUseCase()
        validation_result = validator.validate(
            refactored_code,
            language=request.language,
            progress_callback=lambda msg, pct: update_validation_progress(msg, pct)
        )
        
        # Add validation results to response
        result["validation"] = {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "aws_patterns_found": validation_result.aws_patterns_found,
            "azure_patterns_found": validation_result.azure_patterns_found,
            "syntax_valid": validation_result.syntax_valid,
            "gcp_api_correct": validation_result.gcp_api_correct
        }
        
        update_validation_progress("Validation complete", 100.0)
        
        # Extract variable mapping from result if available
        variable_mapping = {}
        if "variable_mapping" in result:
            variable_mapping = result["variable_mapping"]
        elif "execution_result" in result and isinstance(result["execution_result"], dict):
            # Try to get variable mapping from execution result
            if "variable_mapping" in result["execution_result"]:
                variable_mapping = result["execution_result"]["variable_mapping"]
        
        if variable_mapping:
            result["variable_mapping"] = variable_mapping
        
        # Update job status with result
        migration_jobs[migration_id]["status"] = "completed"
        migration_jobs[migration_id]["result"] = result
        
    except Exception as e:
        # Update job status with error
        migration_jobs[migration_id]["status"] = "failed"
        migration_jobs[migration_id]["result"] = {"error": str(e)}
    finally:
        # Clean up temporary files AFTER we've read the refactored code
        # Don't delete the codebase directory yet - we need it for reading refactored code
        try:
            os.unlink(temp_file_path)
            # Note: We keep the codebase directory until after the result is read by the API endpoint
        except:
            pass  # Best effort cleanup


class AnalyzeRepositoryRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class MigrateRepositoryRequest(BaseModel):
    services: Optional[List[str]] = None
    create_pr: bool = False
    branch_name: Optional[str] = None
    run_tests: bool = False


@app.post("/api/repository/analyze")
async def analyze_repository_endpoint(request: AnalyzeRepositoryRequest):
    """Analyze a Git repository and generate MAR"""
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        credentials = None
        if request.token:
            # Detect provider from URL
            from infrastructure.adapters.git_adapter import GitAdapter
            adapter = GitAdapter()
            provider = adapter.detect_provider(request.repository_url)
            
            credentials = GitCredentials(
                provider=provider,
                token=request.token,
                username=request.username,
                password=request.password
            )
        
        use_case = AnalyzeRepositoryUseCase()
        result = use_case.execute(
            repository_url=request.repository_url,
            branch=request.branch,
            credentials=credentials
        )
        
        if result['success']:
            # Safely serialize MAR
            mar_dict = None
            if result['mar']:
                try:
                    if hasattr(result['mar'], 'to_dict'):
                        mar_dict = result['mar'].to_dict()
                    else:
                        # Fallback: convert to dict manually
                        mar_dict = {
                            'repository_id': result['mar'].repository_id,
                            'repository_url': result['mar'].repository_url,
                            'branch': result['mar'].branch,
                            'generated_at': result['mar'].generated_at.isoformat() if result['mar'].generated_at else None,
                            'total_files': result['mar'].total_files,
                            'total_lines': result['mar'].total_lines,
                            'languages_detected': result['mar'].languages_detected,
                            'services_detected': [
                                {
                                    'service_name': s.service_name,
                                    'service_type': s.service_type,
                                    'files_affected': s.files_affected,
                                    'estimated_changes': s.estimated_changes,
                                    'complexity': s.complexity.value if hasattr(s.complexity, 'value') else str(s.complexity),
                                    'confidence': s.confidence,
                                    'patterns_found': s.patterns_found
                                } for s in result['mar'].services_detected
                            ] if hasattr(result['mar'], 'services_detected') else [],
                            'total_estimated_changes': result['mar'].total_estimated_changes,
                            'files_to_modify': result['mar'].files_to_modify,
                            'files_to_modify_count': result['mar'].files_to_modify_count,
                            'confidence_score': result['mar'].confidence_score,
                            'overall_risk': result['mar'].overall_risk.value if hasattr(result['mar'].overall_risk, 'value') else str(result['mar'].overall_risk),
                            'risks': result['mar'].risks,
                            'estimated_duration_minutes': result['mar'].estimated_duration_minutes
                        }
                except Exception as e:
                    logger.warning(f"Error serializing MAR: {e}")
                    mar_dict = None
            
            return {
                "success": True,
                "repository_id": result['repository_id'],
                "mar": mar_dict,
                "repository": {
                    "id": result['repository'].id,
                    "url": result['repository'].url,
                    "branch": result['repository'].branch,
                    "status": result['repository'].status.value,
                    "total_files": result['repository'].total_files,
                    "total_lines": result['repository'].total_lines,
                }
            }
        else:
            error_msg = result.get('error', 'Analysis failed')
            # Determine appropriate status code based on error type
            status_code = 400
            if 'Authentication failed' in error_msg or 'Authentication' in error_msg:
                status_code = 401
            elif 'not found' in error_msg.lower() or 'Repository not found' in error_msg:
                status_code = 404
            elif 'Timeout' in error_msg or 'timeout' in error_msg.lower():
                status_code = 408
            elif 'Network error' in error_msg or 'connection' in error_msg.lower():
                status_code = 503
            
            raise HTTPException(status_code=status_code, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        
        # Log the full error for debugging
        logger.error(f"Error analyzing repository: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")
        print(f"ERROR analyzing repository: {error_msg}")
        print(f"Traceback: {error_traceback}")
        
        # Determine appropriate status code based on error type
        status_code = 500
        if 'Authentication' in error_msg or '401' in error_msg:
            status_code = 401
        elif 'not found' in error_msg.lower() or '404' in error_msg:
            status_code = 404
        elif 'Timeout' in error_msg or 'timeout' in error_msg.lower():
            status_code = 408
        
        # Include traceback in development mode for debugging
        detail_msg = error_msg
        if os.getenv('DEBUG', 'false').lower() == 'true':
            detail_msg = f"{error_msg}\n\nTraceback:\n{error_traceback}"
        
        raise HTTPException(status_code=status_code, detail=detail_msg)


@app.post("/api/repository/{repository_id}/migrate", response_model=MigrateResponse)
async def migrate_repository_endpoint(repository_id: str, request: MigrateRepositoryRequest, background_tasks: BackgroundTasks):
    """Initiate a repository migration process (async)"""
    try:
        from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
        
        repo_repo = RepositoryRepositoryAdapter()
        repository = repo_repo.load(repository_id)
        
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if not repository.local_path:
            raise HTTPException(status_code=400, detail="Repository not cloned. Please analyze first.")
        
        # Create migration ID
        migration_id = f"repo_mig_{uuid4().hex[:8]}"
        
        # Store job info
        migration_jobs[migration_id] = {
            "status": "pending",
            "repository_id": repository_id,
            "request": request,
            "created_at": datetime.now(),
            "result": None
        }
        
        # Initialize progress tracking
        job_progress[migration_id] = {
            "refactoring": {"progress": 0.0, "message": "Initializing..."},
            "validation": {"progress": 0.0, "message": "Waiting..."}
        }
        
        # Start migration in background
        background_tasks.add_task(execute_repository_migration, migration_id, repository_id, request)
        
        return MigrateResponse(
            migration_id=migration_id,
            status="pending",
            message="Repository migration started",
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error(f"Error initiating repository migration: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")
        print(f"ERROR initiating repository migration: {error_msg}")
        print(f"Traceback: {error_traceback}")
        
        raise HTTPException(status_code=500, detail=error_msg)


def execute_repository_migration(migration_id: str, repository_id: str, request: MigrateRepositoryRequest):
    """Execute repository migration in the background with progress tracking"""
    try:
        # Update status to in progress
        migration_jobs[migration_id]["status"] = "in_progress"
        
        # Progress tracking functions
        def update_refactoring_progress(message: str, progress: float):
            if migration_id in job_progress:
                job_progress[migration_id]["refactoring"] = {
                    "progress": progress,
                    "message": message
                }
        
        def update_validation_progress(message: str, progress: float):
            if migration_id in job_progress:
                job_progress[migration_id]["validation"] = {
                    "progress": progress,
                    "message": message
                }
        
        update_refactoring_progress("Loading repository...", 5.0)
        
        from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
        from infrastructure.adapters.mar_generator import MARGenerator
        
        repo_repo = RepositoryRepositoryAdapter()
        repository = repo_repo.load(repository_id)
        
        if not repository:
            migration_jobs[migration_id]["status"] = "failed"
            migration_jobs[migration_id]["result"] = {"error": "Repository not found"}
            return
        
        if not repository.local_path:
            migration_jobs[migration_id]["status"] = "failed"
            migration_jobs[migration_id]["result"] = {"error": "Repository not cloned"}
            return
        
        # Regenerate MAR
        update_refactoring_progress("Analyzing repository...", 15.0)
        mar_generator = MARGenerator()
        mar = mar_generator.generate_mar(
            repository_path=repository.local_path,
            repository_id=repository.id,
            repository_url=repository.url,
            branch=repository.branch
        )
        
        # Execute migration
        update_refactoring_progress(f"Refactoring {len(request.services or [])} service(s)...", 30.0)
        use_case = ExecuteRepositoryMigrationUseCase()
        result = use_case.execute(
            repository_id=repository_id,
            mar=mar,
            services_to_migrate=request.services,
            run_tests=request.run_tests
        )
        update_refactoring_progress("Refactoring complete", 90.0)
        
        # Validate refactored files
        update_validation_progress("Starting validation...", 0.0)
        from application.use_cases.validate_gcp_code_use_case import ValidateGCPCodeUseCase
        
        validator = ValidateGCPCodeUseCase()
        validation_results = {}
        
        if result.get('refactored_files'):
            total_files = len(result['refactored_files'])
            for idx, (file_path, file_content) in enumerate(result['refactored_files'].items()):
                if file_content:
                    update_validation_progress(f"Validating {file_path}...", (idx / total_files) * 90.0)
                    validation_result = validator.validate(
                        file_content,
                        language='python' if file_path.endswith('.py') else 'java',
                        progress_callback=lambda msg, pct: update_validation_progress(
                            f"{file_path}: {msg}", 
                            ((idx / total_files) * 90.0) + (pct * 0.9 / total_files)
                        )
                    )
                    validation_results[file_path] = {
                        "is_valid": validation_result.is_valid,
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings,
                        "aws_patterns_found": validation_result.aws_patterns_found,
                        "azure_patterns_found": validation_result.azure_patterns_found
                    }
        
        update_validation_progress("Validation complete", 100.0)
        update_refactoring_progress("Refactoring complete", 100.0)
        
        # Create PR if requested
        pr_url = None
        if request.create_pr and result['success']:
            try:
                from infrastructure.adapters.pr_manager import PRManager
                pr_manager = PRManager()
                pr_result = pr_manager.create_migration_pr(
                    repository=repository,
                    mar=mar,
                    branch_name=request.branch_name
                )
                if pr_result['success']:
                    pr_url = pr_result.get('pr_url')
            except Exception as e:
                print(f"PR creation failed: {e}")
        
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        # Log migration results for debugging
        logger.info(f"Migration result: success={result.get('success')}, "
                   f"files_changed={result.get('total_files_changed', 0)}, "
                   f"files_failed={result.get('total_files_failed', 0)}")
        
        if result.get('files_failed'):
            for failure in result.get('files_failed', []):
                logger.error(f"Failed file: {failure.get('file', 'unknown')}, "
                           f"error: {failure.get('error', 'unknown error')}")
        
        response_data = {
            "success": result['success'],
            "repository_id": repository_id,
            "files_changed": result.get('files_changed', []),
            "files_failed": result.get('files_failed', []),
            "total_files_changed": result.get('total_files_changed', 0),
            "total_files_failed": result.get('total_files_failed', 0),
            "test_results": result.get('test_results'),
            "pr_url": pr_url,
            "error": result.get('error'),
            "refactored_files": result.get('refactored_files', {}),
            "validation": validation_results
        }
        
        # Update job status
        migration_jobs[migration_id]["status"] = "completed" if result['success'] else "failed"
        migration_jobs[migration_id]["result"] = response_data
        
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        
        logger.error(f"Error executing repository migration: {error_msg}")
        logger.error(f"Traceback: {error_traceback}")
        print(f"ERROR executing repository migration: {error_msg}")
        print(f"Traceback: {error_traceback}")
        
        migration_jobs[migration_id]["status"] = "failed"
        migration_jobs[migration_id]["result"] = {"error": error_msg}


@app.get("/api/repository/{repository_id}/files/{file_path:path}")
async def get_refactored_file(repository_id: str, file_path: str):
    """Get refactored file content"""
    try:
        from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
        import os
        
        repo_repo = RepositoryRepositoryAdapter()
        repository = repo_repo.load(repository_id)
        
        if not repository or not repository.local_path:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        full_path = os.path.join(repository.local_path, file_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "file_path": file_path,
            "content": content,
            "size": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repository/list")
async def list_repositories():
    """List all analyzed repositories"""
    try:
        from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
        import os
        
        repo_repo = RepositoryRepositoryAdapter()
        storage_path = repo_repo.storage_path
        
        if not os.path.exists(storage_path):
            return {"repositories": []}
        
        repositories = []
        for filename in os.listdir(storage_path):
            if filename.endswith('.json'):
                repo_id = filename[:-5]
                repo = repo_repo.load(repo_id)
                if repo:
                    repositories.append({
                        "id": repo.id,
                        "url": repo.url,
                        "branch": repo.branch,
                        "status": repo.status.value,
                        "total_files": repo.total_files,
                        "total_lines": repo.total_lines,
                        "created_at": repo.created_at.isoformat(),
                    })
        
        return {"repositories": repositories}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)