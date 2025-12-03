#!/usr/bin/env python3
"""
Comprehensive Test Runner

Runs all unit tests in the project with detailed reporting.
This script ensures all tests pass before deployment.
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def discover_and_run_tests():
    """Discover and run all tests"""
    # Discover tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add comprehensive test suites
    test_files = [
        'tests.application.test_use_cases_comprehensive',
        'tests.application.test_use_cases',
        'tests.domain.test_domain_entities_comprehensive',
        'tests.domain.test_domain_entities',
        'tests.infrastructure.test_adapters_comprehensive',
        'tests.infrastructure.test_adapters_repositories',
    ]
    
    # Try to load each test module
    for test_module in test_files:
        try:
            module = __import__(test_module, fromlist=[''])
            discovered = loader.loadTestsFromModule(module)
            suite.addTest(discovered)
            print(f"✓ Loaded {test_module}")
        except ImportError as e:
            print(f"⚠ Skipped {test_module}: {e}")
        except Exception as e:
            print(f"✗ Error loading {test_module}: {e}")
    
    # Also try discovery from tests directory
    try:
        discovered = loader.discover(
            str(project_root / 'tests'),
            pattern='test_*.py',
            top_level_dir=str(project_root)
        )
        suite.addTest(discovered)
    except Exception as e:
        print(f"⚠ Test discovery warning: {e}")
    
    # Run tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        buffer=True,
        stream=sys.stdout
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"\n{test}")
            print(traceback)
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"\n{test}")
            print(traceback)
    
    print("="*70)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = discover_and_run_tests()
    sys.exit(exit_code)
