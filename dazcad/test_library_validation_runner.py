"""Validation runner for comprehensive library file testing."""

import unittest

try:
    from .cadquery_file_validator import validate_cadquery_file
except ImportError:
    # Fallback for direct execution
    from cadquery_file_validator import validate_cadquery_file


def run_comprehensive_validation(all_files, library_path, test_case):
    """Run comprehensive validation on all library files.
    
    Args:
        all_files: List of library file names
        library_path: Path to library directory
        test_case: Test case instance for assertions
    """
    # Track overall results
    all_results = []
    files_with_errors = []
    total_files = len(all_files)
    total_objects = 0
    total_export_tests = 0
    successful_exports = 0

    # Test each file
    for filename in all_files:
        file_path = library_path / filename

        with test_case.subTest(library_file=filename):
            # Run comprehensive validation
            result = validate_cadquery_file(file_path, verbose=True)
            all_results.append(result)

            # Update statistics
            summary = result.get('summary', {})
            total_objects += summary.get('total_objects', 0)
            total_export_tests += summary.get('total_export_tests', 0)
            successful_exports += summary.get('successful_exports', 0)

            # Check if file had errors
            if not result['success']:
                files_with_errors.append(filename)

            # Assert that the file executes successfully
            # We allow export failures but not execution failures
            if result['execution_error']:
                test_case.fail(f"{filename}: {result['execution_error']}")

            # Assert that we got at least one object
            test_case.assertGreater(summary.get('total_objects', 0), 0,
                             f"No exportable objects found in {filename}")

    # Print comprehensive summary
    print(f"\n{'='*60}")
    print("Library Files Test Summary")
    print(f"{'='*60}")
    print(f"Total library files tested: {total_files}")
    print(f"Files with issues: {len(files_with_errors)}")
    print(f"Total objects found: {total_objects}")
    print(f"Total export tests: {total_export_tests}")
    print(f"Successful exports: {successful_exports}")

    if total_export_tests > 0:
        success_rate = successful_exports / total_export_tests * 100
        print(f"Export success rate: {success_rate:.1f}%")

    if files_with_errors:
        print(f"\nFiles with issues: {', '.join(files_with_errors)}")
        print("⚠️  WARNING: Some library files have export issues that may need fixing.")
    else:
        print("\n✅ All library files validated successfully!")


class TestValidationRunner(unittest.TestCase):
    """Tests for validation runner."""

    def test_run_comprehensive_validation_function_exists(self):
        """Test that run_comprehensive_validation function exists."""
        self.assertTrue(callable(run_comprehensive_validation))
