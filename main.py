#!/usr/bin/env python3
"""
Main entry point for the Extended Cloud Refactor Agent

This script demonstrates the usage of the Cloud Refactor Agent system
for migrating multiple AWS services to their Google Cloud equivalents.
Supports both local codebase and repository-level migration.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from infrastructure.adapters.s3_gcs_migration import create_multi_service_migration_system
from domain.entities.codebase import ProgrammingLanguage
from infrastructure.adapters.service_mapping import ServiceMapper
from application.use_cases.analyze_repository_use_case import AnalyzeRepositoryUseCase
from application.use_cases.execute_repository_migration_use_case import ExecuteRepositoryMigrationUseCase
from infrastructure.adapters.git_adapter import GitCredentials, GitProvider
from infrastructure.adapters.pr_manager import PRManager


def main():
    parser = argparse.ArgumentParser(
        description='Universal Cloud Refactor Agent - Migrate AWS/Azure services to GCP equivalents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local codebase migration
  python main.py /path/to/codebase --language python --services s3 lambda

  # Repository-level migration
  python main.py repo analyze https://github.com/user/repo.git
  python main.py repo migrate <repository_id> --create-pr
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Local codebase migration (existing functionality)
    local_parser = subparsers.add_parser('local', help='Migrate local codebase (default)')
    local_parser.add_argument('codebase_path', help='Path to the codebase to refactor')
    local_parser.add_argument('--language', choices=['python', 'java'], default='python',
                              help='Programming language of the codebase (default: python)')
    local_parser.add_argument('--services', nargs='*',
                              help='Specific AWS/Azure services to migrate (e.g., s3 lambda blob_storage functions)')
    local_parser.add_argument('--verbose', '-v', action='store_true',
                              help='Enable verbose output')
    
    # Repository-level commands
    repo_parser = subparsers.add_parser('repo', help='Repository-level migration commands')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_command', help='Repository command')
    
    # Analyze repository
    analyze_parser = repo_subparsers.add_parser('analyze', help='Analyze repository and generate MAR')
    analyze_parser.add_argument('repository_url', help='Git repository URL')
    analyze_parser.add_argument('--branch', default='main', help='Branch to analyze (default: main)')
    analyze_parser.add_argument('--token', help='Git provider token (GitHub/GitLab/Bitbucket)')
    analyze_parser.add_argument('--username', help='Git username (for Bitbucket)')
    analyze_parser.add_argument('--password', help='Git password/app_password (for Bitbucket)')
    analyze_parser.add_argument('--output', help='Output MAR to file (JSON or Markdown)')
    analyze_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    # Execute migration
    migrate_parser = repo_subparsers.add_parser('migrate', help='Execute repository migration')
    migrate_parser.add_argument('repository_id', help='Repository ID from analysis')
    migrate_parser.add_argument('--services', nargs='*', help='Specific services to migrate')
    migrate_parser.add_argument('--create-pr', action='store_true', help='Create Pull Request after migration')
    migrate_parser.add_argument('--branch-name', help='Branch name for PR (auto-generated if not provided)')
    migrate_parser.add_argument('--run-tests', action='store_true', help='Run tests after migration')
    migrate_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    # List repositories
    list_parser = repo_subparsers.add_parser('list', help='List analyzed repositories')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    # For backward compatibility, if no command is provided, treat as local migration
    args = parser.parse_args()
    
    if args.command is None:
        # Backward compatibility: treat positional args as local migration
        if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
            # Re-parse with local command
            sys.argv.insert(1, 'local')
            args = parser.parse_args()
        else:
            parser.print_help()
            sys.exit(1)

    # Route to appropriate handler
    if args.command == 'local':
        handle_local_migration(args)
    elif args.command == 'repo':
        if args.repo_command == 'analyze':
            handle_repository_analyze(args)
        elif args.repo_command == 'migrate':
            handle_repository_migrate(args)
        elif args.repo_command == 'list':
            handle_repository_list(args)
        else:
            repo_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


def handle_local_migration(args):
    """Handle local codebase migration"""
    # Map language argument to ProgrammingLanguage enum
    language_map = {
        'python': ProgrammingLanguage.PYTHON,
        'java': ProgrammingLanguage.JAVA
    }
    language = language_map[args.language]

    # Validate codebase path
    if not Path(args.codebase_path).exists():
        print(f"Error: Codebase path '{args.codebase_path}' does not exist")
        sys.exit(1)

    # Validate service arguments if provided
    if args.services:
        valid_services = [service.value for service in ServiceMapper.get_aws_services()]
        for service in args.services:
            if service.lower() not in valid_services:
                print(f"Warning: Service '{service}' may not be recognized")

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


def handle_repository_analyze(args):
    """Handle repository analysis"""
    from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
    
    if args.verbose:
        print(f"Analyzing repository: {args.repository_url}")
        print(f"Branch: {args.branch}")
    
    # Prepare credentials
    credentials = None
    if args.token:
        # Detect provider from URL
        from infrastructure.adapters.git_adapter import GitAdapter
        adapter = GitAdapter()
        provider = adapter.detect_provider(args.repository_url)
        
        credentials = GitCredentials(
            provider=provider,
            token=args.token,
            username=args.username,
            password=args.password
        )
    
    try:
        # Execute analysis
        use_case = AnalyzeRepositoryUseCase()
        result = use_case.execute(
            repository_url=args.repository_url,
            branch=args.branch,
            credentials=credentials
        )
        
        if result['success']:
            print(f"\n✓ Repository analysis completed successfully!")
            print(f"Repository ID: {result['repository_id']}")
            print(f"Total Files: {result['mar'].total_files}")
            print(f"Total Lines: {result['mar'].total_lines:,}")
            print(f"Languages: {', '.join(result['mar'].languages_detected)}")
            print(f"\nServices Detected: {len(result['mar'].services_detected)}")
            for service in result['mar'].services_detected:
                print(f"  - {service.service_name} ({service.service_type}) - {len(service.files_affected)} files")
            
            print(f"\nEstimated Changes: {result['mar'].total_estimated_changes:,} lines")
            print(f"Files to Modify: {result['mar'].files_to_modify_count}")
            print(f"Confidence Score: {result['mar'].confidence_score:.1%}")
            print(f"Overall Risk: {result['mar'].overall_risk.value.upper()}")
            
            # Save MAR if output specified
            if args.output:
                if args.output.endswith('.md'):
                    with open(args.output, 'w') as f:
                        f.write(result['mar'].to_markdown())
                    print(f"\nMAR saved to: {args.output} (Markdown)")
                else:
                    import json
                    with open(args.output, 'w') as f:
                        json.dump(result['mar'].to_dict(), f, indent=2)
                    print(f"\nMAR saved to: {args.output} (JSON)")
            
            print(f"\nTo migrate this repository, run:")
            print(f"  python main.py repo migrate {result['repository_id']}")
            
            sys.exit(0)
        else:
            print(f"\n✗ Repository analysis failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error during repository analysis: {str(e)}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


def handle_repository_migrate(args):
    """Handle repository migration"""
    from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
    import json
    
    if args.verbose:
        print(f"Migrating repository: {args.repository_id}")
    
    try:
        # Load repository
        repo_repo = RepositoryRepositoryAdapter()
        repository = repo_repo.load(args.repository_id)
        
        if not repository:
            print(f"Error: Repository {args.repository_id} not found")
            print("Please run 'python main.py repo analyze <url>' first")
            sys.exit(1)
        
        # Load MAR (stored in repository metadata or separate file)
        # For now, we'll regenerate it if needed
        from infrastructure.adapters.mar_generator import MARGenerator
        mar_generator = MARGenerator()
        
        if not repository.local_path:
            print("Error: Repository not cloned. Please run analysis first.")
            sys.exit(1)
        
        # Regenerate MAR
        mar = mar_generator.generate_mar(
            repository_path=repository.local_path,
            repository_id=repository.id,
            repository_url=repository.url,
            branch=repository.branch
        )
        
        # Execute migration
        use_case = ExecuteRepositoryMigrationUseCase()
        result = use_case.execute(
            repository_id=args.repository_id,
            mar=mar,
            services_to_migrate=args.services,
            run_tests=args.run_tests
        )
        
        if result['success']:
            print(f"\n✓ Migration completed successfully!")
            print(f"Files Changed: {result['total_files_changed']}")
            print(f"Files Failed: {result['total_files_failed']}")
            
            if result.get('files_failed'):
                print("\nFailed Files:")
                for failed in result['files_failed']:
                    print(f"  - {failed['file']}: {failed['error']}")
            
            # Display test results if available
            if result.get('test_results'):
                test_results = result['test_results']
                print(f"\nTest Results ({test_results['framework']}):")
                print(f"  Total: {test_results['total_tests']}")
                print(f"  Passed: {test_results['passed']}")
                print(f"  Failed: {test_results['failed']}")
                print(f"  Skipped: {test_results['skipped']}")
                print(f"  Status: {'PASSED' if test_results['success'] else 'FAILED'}")
            
            # Create PR if requested
            if args.create_pr:
                print("\nCreating Pull Request...")
                pr_manager = PRManager()
                pr_result = pr_manager.create_migration_pr(
                    repository=repository,
                    mar=mar,
                    branch_name=args.branch_name
                )
                
                if pr_result['success']:
                    print(f"✓ Pull Request created: {pr_result.get('pr_url', 'N/A')}")
                else:
                    print(f"✗ Failed to create PR: {pr_result.get('error', 'Unknown error')}")
                    if pr_result.get('branch_name'):
                        print(f"Branch created: {pr_result['branch_name']}")
                        print("Please create PR manually using the provided branch.")
            
            sys.exit(0)
        else:
            print(f"\n✗ Migration failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error during repository migration: {str(e)}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


def handle_repository_list(args):
    """List analyzed repositories"""
    from infrastructure.repositories.repository_repository import RepositoryRepositoryAdapter
    import os
    
    repo_repo = RepositoryRepositoryAdapter()
    storage_path = repo_repo.storage_path
    
    if not os.path.exists(storage_path):
        print("No repositories analyzed yet.")
        sys.exit(0)
    
    repositories = []
    for filename in os.listdir(storage_path):
        if filename.endswith('.json'):
            repo_id = filename[:-5]
            repo = repo_repo.load(repo_id)
            if repo:
                repositories.append(repo)
    
    if not repositories:
        print("No repositories analyzed yet.")
        sys.exit(0)
    
    print(f"\nAnalyzed Repositories ({len(repositories)}):\n")
    for repo in repositories:
        print(f"ID: {repo.id}")
        print(f"  URL: {repo.url}")
        print(f"  Branch: {repo.branch}")
        print(f"  Status: {repo.status.value}")
        print(f"  Files: {repo.total_files}, Lines: {repo.total_lines:,}")
        print()


if __name__ == "__main__":
    main()