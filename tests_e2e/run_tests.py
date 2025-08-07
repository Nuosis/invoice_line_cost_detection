#!/usr/bin/env python3
"""
End-to-End Test Runner for Invoice Rate Detection System

This script provides a convenient way to run all e2e tests with proper
configuration and reporting.

Usage:
    python e2e_tests/run_tests.py
    python e2e_tests/run_tests.py --verbose
    python e2e_tests/run_tests.py --test-pattern "test_initial*"
"""

import argparse
import logging
import sys
import unittest
from pathlib import Path


def setup_logging(verbose: bool = False):
    """
    Configure logging for test execution.
    
    Args:
        verbose: If True, enable debug logging
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_test_suites():
    """
    Get organized information about available test suites.
    
    Returns:
        dict: Dictionary mapping test categories to test files
    """
    return {
        "Core System Tests": [
            "test_initial_database_setup.py",
            "test_status_command.py"
        ],
        "Parts Management": [
            "test_parts_management.py"
        ],
        "Invoice Processing": [
            "test_invoice_processing.py"
        ],
        "Database Management": [
            "test_database_management.py"
        ],
        "Configuration Management": [
            "test_configuration_management.py"
        ],
        "Discovery Management": [
            "test_discovery_management.py"
        ],
        "Bulk Operations": [
            "test_bulk_operations.py"
        ],
        "Interactive Workflows": [
            "test_interactive_workflows.py"
        ],
        "Cross-Platform Compatibility": [
            "test_cross_platform_compatibility.py"
        ],
        "Error Handling & Edge Cases": [
            "test_error_handling_edge_cases.py"
        ]
    }


def list_test_suites():
    """List all available test suites with descriptions."""
    test_suites = get_test_suites()
    
    print("Available End-to-End Test Suites:")
    print("=" * 50)
    
    for category, test_files in test_suites.items():
        print(f"\n{category}:")
        for test_file in test_files:
            print(f"  • {test_file}")
    
    print(f"\nTotal test files: {sum(len(files) for files in test_suites.values())}")


def discover_and_run_tests(test_pattern: str = "test_*.py", verbose: bool = False, list_suites: bool = False):
    """
    Discover and run all e2e tests.
    
    Args:
        test_pattern: Pattern to match test files
        verbose: If True, run tests with verbose output
        list_suites: If True, list available test suites and exit
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Get the directory containing this script
    test_dir = Path(__file__).parent
    
    # If listing suites, show them and exit
    if list_suites:
        list_test_suites()
        return True
    
    # Show test suite organization
    print("Invoice Rate Detection System - End-to-End Test Suite")
    print("=" * 60)
    
    test_suites = get_test_suites()
    total_suites = len(test_suites)
    total_files = sum(len(files) for files in test_suites.values())
    
    print(f"Test Categories: {total_suites}")
    print(f"Test Files: {total_files}")
    print(f"Test Directory: {test_dir}")
    print(f"Test Pattern: {test_pattern}")
    print("-" * 60)
    
    # Discover tests
    loader = unittest.TestLoader()
    start_dir = str(test_dir)
    suite = loader.discover(start_dir, pattern=test_pattern)
    
    # Configure test runner
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        buffer=True,  # Capture stdout/stderr during tests
        failfast=False,  # Continue running tests after failures
        stream=sys.stdout
    )
    
    # Run tests
    print("Starting test execution...")
    print("-" * 60)
    
    import time
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print detailed summary
    print("=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Execution Time: {end_time - start_time:.2f} seconds")
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # Calculate success rate
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        print("-" * 40)
        for i, (test, traceback) in enumerate(result.failures, 1):
            print(f"{i}. {test}")
            if verbose:
                print(f"   {traceback}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        print("-" * 40)
        for i, (test, traceback) in enumerate(result.errors, 1):
            print(f"{i}. {test}")
            if verbose:
                print(f"   {traceback}")
    
    if result.skipped:
        print(f"\nSKIPPED ({len(result.skipped)}):")
        print("-" * 40)
        for i, (test, reason) in enumerate(result.skipped, 1):
            print(f"{i}. {test}: {reason}")
    
    # Final status
    print("=" * 60)
    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 ALL TESTS PASSED! System is ready for deployment.")
    else:
        print("❌ SOME TESTS FAILED! Please review and fix issues before deployment.")
    print("=" * 60)
    
    # Return success status
    return len(result.failures) == 0 and len(result.errors) == 0


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run end-to-end tests for Invoice Rate Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python e2e_tests/run_tests.py
  python e2e_tests/run_tests.py --verbose
  python e2e_tests/run_tests.py --test-pattern "test_initial*"
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output and debug logging"
    )
    
    parser.add_argument(
        "--test-pattern", "-p",
        default="test_*.py",
        help="Pattern to match test files (default: test_*.py)"
    )
    
    parser.add_argument(
        "--list-suites", "-l",
        action="store_true",
        help="List all available test suites and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Run tests
    success = discover_and_run_tests(args.test_pattern, args.verbose, args.list_suites)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()