"""
FastAPI server for the Cloud Refactor Agent
Provides API endpoints for the frontend application
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
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
    
    return {
        "migration_id": migration_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "result": job["result"],
        "code": job["request"].code  # Include original code for reference
    }


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
        target_file = codebase_path / f"code.{request.language}"
        shutil.copy2(temp_file_path, target_file)
        
        # Create orchestrator and execute migration
        orchestrator = create_multi_service_migration_system()
        result = orchestrator.execute_migration(
            str(codebase_path),
            language,
            services_to_migrate=request.services
        )
        
        # Update job status with result
        migration_jobs[migration_id]["status"] = "completed"
        migration_jobs[migration_id]["result"] = result
        
    except Exception as e:
        # Update job status with error
        migration_jobs[migration_id]["status"] = "failed"
        migration_jobs[migration_id]["result"] = {"error": str(e)}
    finally:
        # Clean up temporary files
        try:
            os.unlink(temp_file_path)
            shutil.rmtree(Path(temp_file_path).parent / "codebase", ignore_errors=True)
        except:
            pass  # Best effort cleanup


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)