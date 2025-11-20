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
from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
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

class MigrateRequest(BaseModel):
    code: str
    language: str
    services: List[str]


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
    """Get the status of a migration job"""
    job = migration_jobs.get(migration_id)
    if not job:
        raise HTTPException(status_code=404, detail="Migration job not found")
    
    response = {
        "migration_id": migration_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "result": job["result"],
        "code": job["request"].code  # Include original code for reference
    }
    
    # If migration completed, include refactored code and variable mapping if available
    if job["status"] == "completed" and job["result"]:
        result = job["result"]
        if isinstance(result, dict):
            # Try to extract refactored code from result
            if "refactored_code" in result:
                response["refactored_code"] = result["refactored_code"]
            elif "execution_result" in result and "refactored_code" in result["execution_result"]:
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
                                response["refactored_code"] = f.read()
                except Exception:
                    pass  # If we can't read it, that's okay
            
            # Extract variable mapping if available
            if "variable_mapping" in result:
                response["variable_mapping"] = result["variable_mapping"]
            elif "execution_result" in result and "variable_mapping" in result["execution_result"]:
                response["variable_mapping"] = result["execution_result"]["variable_mapping"]
    
    return response


def execute_migration(migration_id: str, request: MigrateRequest, temp_file_path: str):
    """Execute the migration in the background"""
    try:
        # Update status to in progress
        migration_jobs[migration_id]["status"] = "in_progress"
        
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
        orchestrator = create_multi_service_migration_system()
        result = orchestrator.execute_migration(
            str(codebase_path),
            language,
            services_to_migrate=request.services
        )
        
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
        except Exception as e:
            print(f"Warning: Could not read refactored code: {e}")
        
        # Add refactored code to result
        if refactored_code:
            result["refactored_code"] = refactored_code
        else:
            # Fallback to original code if transformation didn't happen or file can't be read
            result["refactored_code"] = request.code
        
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


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)