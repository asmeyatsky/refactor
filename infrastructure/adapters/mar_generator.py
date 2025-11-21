"""
Migration Assessment Report (MAR) Generator

Architectural Intent:
- Generates comprehensive pre-migration analysis reports
- Detects cloud services across entire repository
- Estimates changes and calculates confidence scores
"""

import os
import re
from typing import List, Dict, Set
from datetime import datetime
from collections import defaultdict

from domain.value_objects.mar import (
    MigrationAssessmentReport, DetectedService, CrossFileDependency,
    InfrastructureFile, ServiceComplexity, RiskLevel
)
from infrastructure.adapters.service_mapping import ExtendedCodeAnalyzer
from infrastructure.adapters.dependency_graph_builder import DependencyGraphBuilder
from infrastructure.adapters.iac_detector import IACDetector
from infrastructure.adapters.toon_serializer import to_toon


class MARGenerator:
    """
    Generates Migration Assessment Reports (MAR) for repositories
    """
    
    def __init__(self):
        self.code_analyzer = ExtendedCodeAnalyzer()
        self.dependency_builder = DependencyGraphBuilder()
        self.iac_detector = IACDetector()
    
    def generate_mar(self, repository_path: str, repository_id: str, 
                     repository_url: str, branch: str) -> MigrationAssessmentReport:
        """
        Generate Migration Assessment Report for repository
        
        Args:
            repository_path: Path to cloned repository
            repository_id: Unique repository identifier
            repository_url: Repository URL
            branch: Branch name
            
        Returns:
            MigrationAssessmentReport object
        """
        # Detect languages
        languages = self._detect_languages(repository_path)
        
        # Count files and lines
        total_files, total_lines = self._count_files_and_lines(repository_path, languages)
        
        # Detect cloud services
        services_detected = self._detect_cloud_services(repository_path, languages)
        
        # Build dependency graph
        dependencies = self.dependency_builder.build_graph(repository_path, languages)
        
        # Detect infrastructure files using IACDetector
        iac_files = self.iac_detector.detect_iac_files(repository_path)
        infrastructure_files = [
            InfrastructureFile(
                file_path=iac_file.file_path,
                file_type=iac_file.iac_type.value,
                services_referenced=iac_file.services_referenced,
                estimated_changes=iac_file.estimated_changes
            )
            for iac_file in iac_files
        ]
        
        # Calculate estimates
        total_estimated_changes = sum(s.estimated_changes for s in services_detected)
        files_to_modify = self._get_files_to_modify(services_detected, dependencies)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(services_detected, total_files)
        
        # Assess risks
        overall_risk, risks = self._assess_risks(services_detected, dependencies, infrastructure_files)
        
        # Detect tests
        test_files, test_framework = self._detect_tests(repository_path, languages)
        
        # Estimate duration
        estimated_duration = self._estimate_duration(total_estimated_changes, len(services_detected))
        
        # Recommended services
        recommended_services = [s.service_name for s in services_detected if s.confidence > 0.7]
        
        return MigrationAssessmentReport(
            repository_id=repository_id,
            repository_url=repository_url,
            branch=branch,
            generated_at=datetime.now(),
            total_files=total_files,
            total_lines=total_lines,
            languages_detected=languages,
            services_detected=services_detected,
            total_estimated_changes=total_estimated_changes,
            files_to_modify=files_to_modify,
            files_to_modify_count=len(files_to_modify),
            cross_file_dependencies=dependencies,
            infrastructure_files=infrastructure_files,
            confidence_score=confidence_score,
            overall_risk=overall_risk,
            risks=risks,
            existing_tests_found=len(test_files) > 0,
            test_files=test_files,
            test_framework=test_framework,
            recommended_services=recommended_services,
            estimated_duration_minutes=estimated_duration
        )
    
    def _detect_languages(self, repo_path: str) -> List[str]:
        """Detect programming languages in repository"""
        languages = set()
        
        for root, dirs, files in os.walk(repo_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target']]
            
            for file in files:
                if file.endswith('.py'):
                    languages.add('python')
                elif file.endswith('.java'):
                    languages.add('java')
                elif file.endswith('.js') or file.endswith('.ts'):
                    languages.add('javascript')
                elif file.endswith('.go'):
                    languages.add('go')
        
        return list(languages)
    
    def _count_files_and_lines(self, repo_path: str, languages: List[str]) -> tuple:
        """Count total files and lines of code"""
        total_files = 0
        total_lines = 0
        
        extensions = []
        if 'python' in languages:
            extensions.append('.py')
        if 'java' in languages:
            extensions.append('.java')
        if 'javascript' in languages:
            extensions.extend(['.js', '.ts'])
        if 'go' in languages:
            extensions.append('.go')
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            total_lines += len(f.readlines())
                    except Exception:
                        pass
        
        return total_files, total_lines
    
    def _detect_cloud_services(self, repo_path: str, languages: List[str]) -> List[DetectedService]:
        """Detect cloud services across repository"""
        services_detected = []
        service_files: Dict[str, Set[str]] = defaultdict(set)
        service_patterns: Dict[str, List[str]] = defaultdict(list)
        
        # AWS service patterns
        aws_patterns = {
            's3': [r'boto3\.client\([\'"]s3[\'"]', r'boto3\.resource\([\'"]s3[\'"]', r'\.upload_file', r'\.download_file', r'\.get_object', r'\.put_object'],
            'lambda': [r'boto3\.client\([\'"]lambda[\'"]', r'def\s+lambda_handler', r'lambda_client\.invoke'],
            'dynamodb': [r'boto3\.client\([\'"]dynamodb[\'"]', r'boto3\.resource\([\'"]dynamodb[\'"]', r'\.put_item', r'\.get_item', r'\.query'],
            'sqs': [r'boto3\.client\([\'"]sqs[\'"]', r'\.send_message', r'\.receive_message', r'QueueUrl'],
            'sns': [r'boto3\.client\([\'"]sns[\'"]', r'\.publish\(', r'TopicArn'],
        }
        
        # Azure service patterns
        azure_patterns = {
            'blob_storage': [r'BlobServiceClient', r'azure\.storage\.blob', r'\.upload_blob', r'\.download_blob'],
            'functions': [r'azure\.functions', r'func\.HttpRequest', r'@function_app'],
            'cosmos_db': [r'CosmosClient', r'azure\.cosmos', r'\.create_item', r'\.read_item'],
            'service_bus': [r'ServiceBusClient', r'azure\.servicebus', r'\.send_messages'],
        }
        
        all_patterns = {}
        for service, patterns in aws_patterns.items():
            all_patterns[f'aws_{service}'] = patterns
        for service, patterns in azure_patterns.items():
            all_patterns[f'azure_{service}'] = patterns
        
        # Scan all code files
        code_files = self._find_code_files(repo_path, languages)
        
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                relative_path = os.path.relpath(file_path, repo_path)
                
                # Check each service pattern
                for service_name, patterns in all_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            service_files[service_name].add(relative_path)
                            service_patterns[service_name].append(pattern)
                            break
            except Exception:
                continue
        
        # Create DetectedService objects
        for service_name, files in service_files.items():
            service_type = 'aws' if service_name.startswith('aws_') else 'azure'
            clean_name = service_name.replace('aws_', '').replace('azure_', '')
            
            # Estimate changes (rough: 10-50 lines per file depending on complexity)
            estimated_changes = len(files) * 30  # Average estimate
            
            # Determine complexity
            complexity = self._determine_complexity(len(files), len(service_patterns[service_name]))
            
            # Calculate confidence (based on pattern matches and file count)
            confidence = min(0.9, 0.5 + (len(files) * 0.05) + (len(service_patterns[service_name]) * 0.02))
            
            services_detected.append(DetectedService(
                service_name=clean_name,
                service_type=service_type,
                files_affected=list(files),
                estimated_changes=estimated_changes,
                complexity=complexity,
                confidence=confidence,
                patterns_found=list(set(service_patterns[service_name]))
            ))
        
        return services_detected
    
    def _find_code_files(self, repo_path: str, languages: List[str]) -> List[str]:
        """Find all code files in repository"""
        code_files = []
        extensions = []
        
        if 'python' in languages:
            extensions.append('.py')
        if 'java' in languages:
            extensions.append('.java')
        if 'javascript' in languages:
            extensions.extend(['.js', '.ts'])
        if 'go' in languages:
            extensions.append('.go')
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'target']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    code_files.append(os.path.join(root, file))
        
        return code_files
    
    def _determine_complexity(self, file_count: int, pattern_count: int) -> ServiceComplexity:
        """Determine service migration complexity"""
        if file_count <= 2 and pattern_count <= 3:
            return ServiceComplexity.SIMPLE
        elif file_count <= 5 and pattern_count <= 10:
            return ServiceComplexity.MODERATE
        elif file_count <= 15:
            return ServiceComplexity.COMPLEX
        else:
            return ServiceComplexity.VERY_COMPLEX
    
    def _get_files_to_modify(self, services: List[DetectedService], 
                            dependencies: List[CrossFileDependency]) -> List[str]:
        """Get list of all files that need modification"""
        files_set = set()
        
        # Add files from detected services
        for service in services:
            files_set.update(service.files_affected)
        
        # Add files with dependencies that need updating
        for dep in dependencies:
            if dep.dependency_type in ['import', 'constant', 'variable']:
                files_set.add(dep.source_file)
                files_set.add(dep.target_file)
        
        return sorted(list(files_set))
    
    def _calculate_confidence_score(self, services: List[DetectedService], 
                                   total_files: int) -> float:
        """Calculate overall confidence score for migration"""
        if not services:
            return 0.0
        
        # Average confidence of detected services
        avg_service_confidence = sum(s.confidence for s in services) / len(services)
        
        # Penalize if too many files (complexity)
        file_factor = min(1.0, 1000.0 / max(total_files, 1))
        
        # Combine factors
        confidence = (avg_service_confidence * 0.7) + (file_factor * 0.3)
        
        return min(0.95, max(0.1, confidence))
    
    def _assess_risks(self, services: List[DetectedService],
                     dependencies: List[CrossFileDependency],
                     infrastructure_files: List[InfrastructureFile]) -> tuple:
        """Assess migration risks"""
        risks = []
        risk_level = RiskLevel.LOW
        
        # Check for complex services
        complex_services = [s for s in services if s.complexity in [ServiceComplexity.COMPLEX, ServiceComplexity.VERY_COMPLEX]]
        if complex_services:
            risks.append(f"{len(complex_services)} complex service(s) detected requiring careful migration")
            risk_level = RiskLevel.MEDIUM
        
        # Check for many cross-file dependencies
        if len(dependencies) > 50:
            risks.append(f"High number of cross-file dependencies ({len(dependencies)}) may require careful coordination")
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
        
        # Check for infrastructure files
        if infrastructure_files:
            risks.append(f"{len(infrastructure_files)} infrastructure file(s) detected - may require manual review")
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
        
        # Check for low confidence services
        low_confidence = [s for s in services if s.confidence < 0.6]
        if low_confidence:
            risks.append(f"{len(low_confidence)} service(s) with low confidence scores - manual review recommended")
            risk_level = RiskLevel.HIGH
        
        # Check for very complex migrations
        if any(s.complexity == ServiceComplexity.VERY_COMPLEX for s in services):
            risks.append("Very complex service migrations detected - consider phased approach")
            risk_level = RiskLevel.HIGH
        
        if not risks:
            risks.append("No major risks identified")
        
        return risk_level, risks
    
    
    def _detect_tests(self, repo_path: str, languages: List[str]) -> tuple:
        """Detect test files and framework"""
        test_files = []
        test_framework = None
        
        # Test file patterns
        test_patterns = {
            'python': (['test_', '_test.py'], 'pytest'),
            'java': (['Test.java', 'test/'], 'junit'),
            'javascript': (['.test.', '.spec.'], 'jest'),
        }
        
        for root, dirs, files in os.walk(repo_path):
            # Look for test directories
            if 'test' in root.lower() or 'tests' in root.lower():
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo_path)
                    test_files.append(relative_path)
            
            # Look for test files
            for file in files:
                if 'python' in languages:
                    if file.startswith('test_') or file.endswith('_test.py'):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, repo_path)
                        test_files.append(relative_path)
                        if not test_framework:
                            test_framework = 'pytest'
                
                if 'java' in languages:
                    if file.endswith('Test.java'):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, repo_path)
                        test_files.append(relative_path)
                        if not test_framework:
                            test_framework = 'junit'
                
                if 'javascript' in languages:
                    if '.test.' in file or '.spec.' in file:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, repo_path)
                        test_files.append(relative_path)
                        if not test_framework:
                            test_framework = 'jest'
        
        return test_files, test_framework
    
    def _estimate_duration(self, total_changes: int, service_count: int) -> int:
        """Estimate migration duration in minutes"""
        # Base estimate: 1 minute per 100 lines of changes
        base_minutes = total_changes / 100
        
        # Add overhead per service
        service_overhead = service_count * 5
        
        # Add base overhead
        base_overhead = 10
        
        total_minutes = base_minutes + service_overhead + base_overhead
        
        return int(total_minutes)
