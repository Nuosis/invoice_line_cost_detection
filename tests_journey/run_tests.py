#!/usr/bin/env python3
"""
Journey Tests Runner

This script runs all journey tests with proper configuration and reporting.
Journey tests validate complete user interaction flows with the CLI interface.

Usage:
    # Run all journey tests
    PYTHONPATH=. uv run python journey_tests/run_tests.py

    # Run specific test file
    PYTHONPATH=. uv run python journey_tests/run_tests.py --test test_path_input_prompts

    # Run with verbose output
    PYTHONPATH=. uv run python journey_tests/run_tests.py --verbose

    # Run with coverage reporting
    PYTHONPATH=. uv run python journey_tests/run_tests.py --coverage
"""

import sys
import unittest
import argparse
import logging
from pathlib import Path
import importlib.util

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_logging(verbose=False):
    """Configure logging for test execution."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from third-party libraries during tests
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def discover_journey_tests(test_pattern=None):
    """
    Discover and load journey test modules.
    
    Args:
        test_pattern: Optional pattern to filter test files
        
    Returns:
        unittest.TestSuite: Test suite containing all discovered tests
    """
    journey_tests_dir = Path(__file__).parent
    test_suite = unittest.TestSuite()
    
    # Define test files in execution order (most critical first)
    test_files = [
        # Priority 1 - Critical user interaction flows (would have caught the original bug)
        'test_path_input_prompts.py',           # Priority 1 - would have caught the bug
        'test_interactive_command_workflows.py', # Priority 1 - core user experience
        'test_error_recovery_journeys.py',      # Priority 1 - critical error handling
        
        # Priority 2 - Common user interaction patterns
        'test_choice_selection_prompts.py',     # Priority 2 - common interactions
        'test_confirmation_dialogs.py',         # Priority 2 - user confirmations
        
        # Priority 3 - Specific workflow components
        'test_parts_discovery_prompts.py',      # Priority 3 - parts discovery workflows
        'test_output_configuration_prompts.py', # Priority 3 - output configuration
        'test_validation_mode_selection.py',    # Priority 3 - validation mode selection
        
        # Priority 4 - Advanced workflow scenarios
        'test_user_cancellation_flows.py',      # Priority 4 - cancellation handling
        'test_multi_step_workflow_state.py',    # Priority 4 - complex state management
    ]
    
    # Filter test files if pattern provided
    if test_pattern:
        test_files = [f for f in test_files if test_pattern in f]
    
    loaded_tests = 0
    for test_file in test_files:
        test_path = journey_tests_dir / test_file
        
        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_file}")
            continue
            
        try:
            # Load the test module
            spec = importlib.util.spec_from_file_location(
                test_file[:-3],  # Remove .py extension
                test_path
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            
            # Discover tests in the module
            loader = unittest.TestLoader()
            module_tests = loader.loadTestsFromModule(test_module)
            test_suite.addTest(module_tests)
            
            test_count = module_tests.countTestCases()
            loaded_tests += test_count
            print(f"✅ Loaded {test_count} tests from {test_file}")
            
        except Exception as e:
            print(f"❌ Failed to load {test_file}: {e}")
            continue
    
    print(f"\n📊 Total journey tests loaded: {loaded_tests}")
    return test_suite


def run_journey_tests(test_pattern=None, verbose=False, coverage=False):
    """
    Run journey tests with specified configuration.
    
    Args:
        test_pattern: Optional pattern to filter test files
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        
    Returns:
        bool: True if all tests passed, False otherwise
    """
    print("🚀 Starting Journey Tests Execution")
    print("=" * 50)
    
    # Setup logging
    setup_logging(verbose)
    
    # Verify project structure
    docs_invoices = project_root / "docs" / "invoices"
    if not docs_invoices.exists():
        print(f"❌ Required directory not found: {docs_invoices}")
        print("   Journey tests require real PDF files in docs/invoices/")
        return False
    
    target_pdf = docs_invoices / "5790265786.pdf"
    if not target_pdf.exists():
        print(f"❌ Required test file not found: {target_pdf}")
        print("   Journey tests specifically test against 5790265786.pdf")
        return False
    
    print(f"✅ Project structure verified")
    print(f"✅ Target PDF found: {target_pdf}")
    print()
    
    # Discover and load tests
    test_suite = discover_journey_tests(test_pattern)
    
    if test_suite.countTestCases() == 0:
        print("❌ No tests found to run")
        return False
    
    # Configure test runner
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        buffer=True,  # Capture stdout/stderr during tests
        failfast=False,  # Continue running tests after failures
    )
    
    print("\n🧪 Running Journey Tests...")
    print("-" * 30)
    
    # Run the tests
    try:
        result = runner.run(test_suite)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 Journey Tests Summary")
        print("=" * 50)
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
        passed = total_tests - failures - errors - skipped
        
        print(f"Total Tests:  {total_tests}")
        print(f"✅ Passed:    {passed}")
        print(f"❌ Failed:    {failures}")
        print(f"💥 Errors:    {errors}")
        print(f"⏭️  Skipped:   {skipped}")
        
        # Show failure details
        if result.failures:
            print(f"\n❌ Test Failures ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  • {test}")
                if verbose:
                    print(f"    {traceback}")
        
        if result.errors:
            print(f"\n💥 Test Errors ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"  • {test}")
                if verbose:
                    print(f"    {traceback}")
        
        # Overall result
        success = failures == 0 and errors == 0
        if success:
            print(f"\n🎉 All journey tests passed!")
            print("   The CLI user interface is working correctly.")
        else:
            print(f"\n⚠️  Some journey tests failed.")
            print("   There may be issues with CLI user interactions.")
        
        return success
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error during test execution: {e}")
        return False


def main():
    """Main entry point for journey tests runner."""
    parser = argparse.ArgumentParser(
        description="Run journey tests for CLI user interface validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all journey tests
  PYTHONPATH=. uv run python journey_tests/run_tests.py

  # Run specific test file
  PYTHONPATH=. uv run python journey_tests/run_tests.py --test path_input

  # Run with verbose output
  PYTHONPATH=. uv run python journey_tests/run_tests.py --verbose

  # Run with coverage (if coverage.py is installed)
  PYTHONPATH=. uv run python journey_tests/run_tests.py --coverage
        """
    )
    
    parser.add_argument(
        '--test', '-t',
        help='Run specific test file (partial name match)',
        default=None
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with detailed logging'
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Enable coverage reporting (requires coverage.py)'
    )
    
    args = parser.parse_args()
    
    # Run the tests
    success = run_journey_tests(
        test_pattern=args.test,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()