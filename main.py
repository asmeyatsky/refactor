#!/usr/bin/env python3
"""
Main entry point for the Extended Cloud Refactor Agent

This script demonstrates the usage of the Cloud Refactor Agent system
for migrating multiple AWS services to their Google Cloud equivalents.
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
from domain.entities.codebase import ProgrammingLanguage
from infrastructure.adapters.service_mapping import ServiceMapper


def main():
    parser = argparse.ArgumentParser(
        description='Universal Cloud Refactor Agent - Migrate AWS/Azure services to GCP equivalents'
    )
    parser.add_argument('codebase_path', help='Path to the codebase to refactor')
    parser.add_argument('--language', choices=['python', 'java'], default='python',
                       help='Programming language of the codebase (default: python)')
    parser.add_argument('--services', nargs='*',
                       help='Specific AWS/Azure services to migrate (e.g., s3 lambda blob_storage functions)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Validate codebase path
    if not Path(args.codebase_path).exists():
        print(f"Error: Codebase path '{args.codebase_path}' does not exist")
        sys.exit(1)

    # Map language argument to ProgrammingLanguage enum
    language_map = {
        'python': ProgrammingLanguage.PYTHON,
        'java': ProgrammingLanguage.JAVA
    }
    language = language_map[args.language]

    # Validate service arguments if provided
    if args.services:
        valid_services = [service.value for service in ServiceMapper.get_aws_services()]
        for service in args.services:
            if service.lower() not in valid_services:
                print(f"Error: Invalid service '{service}'. Valid services are: {valid_services}")
                sys.exit(1)

    if args.verbose:
        print(f"Starting migration for codebase: {args.codebase_path}")
        print(f"Language: {language.value}")
        if args.services:
            print(f"Services to migrate: {args.services}")
        else:
            print("Service detection: Auto-detecting AWS services in codebase")

    try:
        # Create the multi-service migration system
        orchestrator = create_multi_service_migration_system()

        # Execute the migration
        result = orchestrator.execute_migration(
            args.codebase_path,
            language,
            services_to_migrate=args.services
        )

        # Print results
        print(f"\nMigration completed: {result['migration_id']}")
        print(f"Codebase ID: {result['codebase_id']}")
        print(f"Plan ID: {result['plan_id']}")
        print(f"Migration Type: {result['migration_type']}")
        print(f"Completed at: {result['completed_at']}")

        print(f"\nVerification: {'PASSED' if result['verification_result']['success'] else 'FAILED'}")
        print(f"Security Validation: {'PASSED' if result['security_validation_passed'] else 'FAILED'}")

        if not result['verification_result']['success']:
            print(f"\nErrors: {result['verification_result']['errors']}")

        if result['verification_result']['warnings']:
            print(f"\nWarnings: {result['verification_result']['warnings']}")

        # Print execution results if available
        exec_result = result['execution_result']
        if exec_result.get('service_results'):
            print(f"\nService Migration Results:")
            for service, stats in exec_result['service_results'].items():
                print(f"  {service}: {stats.get('success', 0)} successful, {stats.get('failed', 0)} failed")

        # Return appropriate exit code
        if result['verification_result']['success'] and result['security_validation_passed']:
            if args.verbose:
                print("\nMigration completed successfully!")
            sys.exit(0)
        else:
            print("\nMigration completed but with issues!")
            sys.exit(1)

    except Exception as e:
        print(f"Error during migration: {str(e)}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()