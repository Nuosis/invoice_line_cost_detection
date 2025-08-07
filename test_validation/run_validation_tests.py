"""
Test runner for validation test suite.

This script runs all validation tests and provides comprehensive reporting
on text extraction accuracy, CLI validation output, and expectation matching.
"""

import unittest
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_validation.test_text_extraction_validation import (
    TextExtractionValidationTests
)
from test_validation.test_cli_validation_output import (
    CLIValidationOutputTests,
    CLIValidationIntegrationTests
)
from test_validation.test_expectation_generator import (
    ExpectationGeneratorTests,
    ExpectationTemplateValidationTests
)


class ValidationTestRunner:
    """
    Custom test runner for validation tests with detailed reporting.
    """
    
    def __init__(self):
        """Initialize the test runner."""
        self.results = {
            'text_extraction': {},
            'cli_validation': {},
            'expectation_generation': {},
            'overall': {}
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all validation tests and return comprehensive results.
        
        Returns:
            Dictionary containing test results and statistics
        """
        print("=" * 80)
        print("INVOICE RATE DETECTION SYSTEM - VALIDATION TEST SUITE")
        print("=" * 80)
        print()
        
        start_time = time.time()
        
        # Run text extraction validation tests
        print("1. Running Text Extraction Validation Tests...")
        print("-" * 50)
        text_results = self._run_test_suite(TextExtractionValidationTests)
        self.results['text_extraction'] = text_results
        print()
        
        # Run CLI validation output tests
        print("2. Running CLI Validation Output Tests...")
        print("-" * 50)
        cli_results = self._run_test_suite([
            CLIValidationOutputTests,
            CLIValidationIntegrationTests
        ])
        self.results['cli_validation'] = cli_results
        print()
        
        # Run expectation generator tests
        print("3. Running Expectation Generator Tests...")
        print("-" * 50)
        expectation_results = self._run_test_suite([
            ExpectationGeneratorTests,
            ExpectationTemplateValidationTests
        ])
        self.results['expectation_generation'] = expectation_results
        print()
        
        # Calculate overall results
        total_time = time.time() - start_time
        self.results['overall'] = self._calculate_overall_results(total_time)
        
        # Print summary
        self._print_summary()
        
        return self.results
    
    def _run_test_suite(self, test_classes) -> Dict[str, Any]:
        """
        Run a test suite and return results.
        
        Args:
            test_classes: Test class or list of test classes to run
            
        Returns:
            Dictionary containing test results
        """
        if not isinstance(test_classes, list):
            test_classes = [test_classes]
        
        suite = unittest.TestSuite()
        
        # Add all test methods from each class
        for test_class in test_classes:
            tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run tests with custom result collector
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=sys.stdout,
            buffer=True
        )
        
        result = runner.run(suite)
        
        # Compile results
        return {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / 
                           max(result.testsRun, 1)) * 100,
            'failure_details': [str(failure[1]) for failure in result.failures],
            'error_details': [str(error[1]) for error in result.errors],
            'skipped_details': [str(skip[1]) for skip in result.skipped]
        }
    
    def _calculate_overall_results(self, total_time: float) -> Dict[str, Any]:
        """Calculate overall test results."""
        total_tests = sum(r.get('tests_run', 0) for r in self.results.values() if isinstance(r, dict))
        total_failures = sum(r.get('failures', 0) for r in self.results.values() if isinstance(r, dict))
        total_errors = sum(r.get('errors', 0) for r in self.results.values() if isinstance(r, dict))
        total_skipped = sum(r.get('skipped', 0) for r in self.results.values() if isinstance(r, dict))
        
        overall_success_rate = ((total_tests - total_failures - total_errors) / 
                              max(total_tests, 1)) * 100
        
        return {
            'total_tests': total_tests,
            'total_failures': total_failures,
            'total_errors': total_errors,
            'total_skipped': total_skipped,
            'overall_success_rate': overall_success_rate,
            'total_time': total_time,
            'status': 'PASS' if total_failures == 0 and total_errors == 0 else 'FAIL'
        }
    
    def _print_summary(self):
        """Print comprehensive test summary."""
        print("=" * 80)
        print("VALIDATION TEST SUITE SUMMARY")
        print("=" * 80)
        
        overall = self.results['overall']
        
        print(f"Total Tests Run: {overall['total_tests']}")
        print(f"Passed: {overall['total_tests'] - overall['total_failures'] - overall['total_errors']}")
        print(f"Failed: {overall['total_failures']}")
        print(f"Errors: {overall['total_errors']}")
        print(f"Skipped: {overall['total_skipped']}")
        print(f"Success Rate: {overall['overall_success_rate']:.1f}%")
        print(f"Total Time: {overall['total_time']:.2f} seconds")
        print(f"Overall Status: {overall['status']}")
        print()
        
        # Print detailed results by category
        categories = [
            ('Text Extraction Tests', 'text_extraction'),
            ('CLI Validation Tests', 'cli_validation'),
            ('Expectation Generator Tests', 'expectation_generation')
        ]
        
        for category_name, category_key in categories:
            if category_key in self.results:
                results = self.results[category_key]
                print(f"{category_name}:")
                print(f"  Tests: {results.get('tests_run', 0)}")
                print(f"  Success Rate: {results.get('success_rate', 0):.1f}%")
                if results.get('failures', 0) > 0:
                    print(f"  Failures: {results.get('failures', 0)}")
                if results.get('errors', 0) > 0:
                    print(f"  Errors: {results.get('errors', 0)}")
                if results.get('skipped', 0) > 0:
                    print(f"  Skipped: {results.get('skipped', 0)}")
                print()
        
        # Print failure details if any
        if overall['total_failures'] > 0 or overall['total_errors'] > 0:
            print("FAILURE/ERROR DETAILS:")
            print("-" * 40)
            
            for category_key, results in self.results.items():
                if isinstance(results, dict):
                    if results.get('failure_details'):
                        print(f"{category_key.upper()} FAILURES:")
                        for detail in results['failure_details'][:3]:  # Show first 3
                            print(f"  {detail[:200]}...")
                        print()
                    
                    if results.get('error_details'):
                        print(f"{category_key.upper()} ERRORS:")
                        for detail in results['error_details'][:3]:  # Show first 3
                            print(f"  {detail[:200]}...")
                        print()
        
        print("=" * 80)


def main():
    """Main entry point for validation test runner."""
    runner = ValidationTestRunner()
    results = runner.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['overall']['status'] == 'PASS' else 1
    sys.exit(exit_code)


if __name__ == '__main__':
    main()