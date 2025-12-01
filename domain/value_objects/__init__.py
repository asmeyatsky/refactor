"""
Value Objects

Architectural Intent:
- Represent concepts that are identified by their attributes rather than identity
- Provide type safety and validation for common domain concepts
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


@dataclass(frozen=True)
class MigrationType:
    """Represents the type of cloud migration"""
    source: str  # e.g., "AWS"
    target: str  # e.g., "GCP"
    service: str  # e.g., "S3 to GCS"

    def __str__(self) -> str:
        return f"{self.source} to {self.target} ({self.service})"


@dataclass(frozen=True)
class ServiceMapping:
    """Represents how services map between cloud providers"""
    source_service: str
    target_service: str
    source_api_calls: List[str]
    target_api_calls: List[str]
    authentication_mapping: dict
    config_mapping: dict = None


@dataclass(frozen=True)
class RefactoringResult:
    """Result of a refactoring operation"""
    success: bool
    message: str
    transformed_files: int
    errors: list
    warnings: list
    service_results: dict = None  # Results for each service refactored
    variable_mapping: dict = None  # Variable name changes for propagation


@dataclass(frozen=True)
class CloudProvider:
    """Represents a cloud provider"""
    name: str
    sdk_package: str
    authentication_type: str


class RefactoringOperationType(Enum):
    """Types of refactoring operations"""
    API_REPLACEMENT = "api_replacement"
    AUTHENTICATION_TRANSLATION = "authentication_translation"
    CONFIGURATION_UPDATE = "configuration_update"
    DEPENDENCY_UPDATE = "dependency_update"
    CODE_STRUCTURE_CHANGE = "code_structure_change"
    SERVICE_MIGRATION = "service_migration"


class CloudProvider(Enum):
    """Cloud providers supported for migration"""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class AWSService(Enum):
    """AWS Services supported for migration"""
    S3 = "s3"
    LAMBDA = "lambda"
    DYNAMODB = "dynamodb"
    SQS = "sqs"
    SNS = "sns"
    RDS = "rds"
    EC2 = "ec2"
    IAM = "iam"
    CLOUDWATCH = "cloudwatch"
    API_GATEWAY = "apigateway"
    ELASTICACHE = "elasticache"
    EKS = "eks"
    FARGATE = "fargate"


class AzureService(Enum):
    """Azure Services supported for migration - Top 15 Azure Services"""
    BLOB_STORAGE = "blob_storage"
    FUNCTIONS = "functions"
    COSMOS_DB = "cosmos_db"
    SERVICE_BUS = "service_bus"
    EVENT_HUBS = "event_hubs"
    SQL_DATABASE = "sql_database"
    VIRTUAL_MACHINES = "virtual_machines"
    MONITOR = "monitor"
    API_MANAGEMENT = "api_management"
    REDIS_CACHE = "redis_cache"
    AKS = "aks"
    CONTAINER_INSTANCES = "container_instances"
    APP_SERVICE = "app_service"
    KEY_VAULT = "key_vault"
    APPLICATION_INSIGHTS = "application_insights"


class GCPService(Enum):
    """GCP Services that correspond to AWS/Azure services"""
    CLOUD_STORAGE = "cloud_storage"
    CLOUD_FUNCTIONS = "cloud_functions"
    CLOUD_RUN = "cloud_run"
    FIRESTORE = "firestore"
    BIGTABLE = "bigtable"
    PUB_SUB = "pub_sub"
    CLOUD_SQL = "cloud_sql"
    COMPUTE_ENGINE = "compute_engine"
    IAM = "iam"
    CLOUD_MONITORING = "cloud_monitoring"
    CLOUD_ENDPOINTS = "cloud_endpoints"
    APIGEE = "apigee"
    GKE = "gke"
    MEMORYSTORE = "memorystore"
    CLOUD_BUILD = "cloud_build"
    CLOUD_DEPLOY = "cloud_deploy"
    SECRET_MANAGER = "secret_manager"