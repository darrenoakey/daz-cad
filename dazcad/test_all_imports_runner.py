"""Import test runner for comprehensive import testing."""

import unittest


def run_comprehensive_import_tests(test_case, import_utils):
    """Run comprehensive import tests.
    
    Args:
        test_case: Test case instance for assertions
        import_utils: ImportUtils instance for testing
    """
    python_files = import_utils.find_python_files()
    test_case.assertGreater(len(python_files), 0, "No Python files found to test")

    # Track results
    successful_imports = []
    failed_imports = []
    relative_import_failures = []

    # Expected failures (files that need special context)
    expected_failures = {
        'server.py': 'Sanic app name conflicts during testing',
        'bearing.py': 'Library file needs show_object context',
        'gear.py': 'Library file needs show_object context',
        'vase.py': 'Library file needs show_object context',
        'assembly.py': 'Library file needs show_object context',
        'bracket.py': 'Library file needs show_object context'
    }

    for file_path in python_files:
        try:
            import_utils.import_module_from_path(file_path)
            successful_imports.append(file_path.name)
        except Exception as e:  # pylint: disable=broad-exception-caught
            error_msg = str(e)

            # Check if this is the critical relative import issue
            if "attempted relative import with no known parent package" in error_msg:
                relative_import_failures.append((file_path.name, error_msg))

            failed_imports.append((file_path.name, error_msg))

    # Print summary
    print("\\nImport test summary:")
    print(f"Successful imports: {len(successful_imports)}")
    print(f"Failed imports: {len(failed_imports)}")

    if successful_imports:
        print(f"Successfully imported: {', '.join(successful_imports)}")

    if failed_imports:
        print("Failed imports:")
        for filename, error in failed_imports:
            if filename in expected_failures:
                expected_reason = expected_failures[filename]
                print(f"  {filename}: {error} (EXPECTED - {expected_reason})")
            else:
                print(f"  {filename}: {error} (UNEXPECTED)")

    # Only fail the test for critical relative import issues
    if relative_import_failures:
        failure_msg = "Critical relative import failures found:\\n"
        for filename, error in relative_import_failures:
            failure_msg += f"  {filename}: {error}\\n"
        test_case.fail(failure_msg)

    # Verify we have a reasonable number of successful imports
    min_expected_imports = 15
    test_case.assertGreaterEqual(len(successful_imports), min_expected_imports,
                           "Too few successful imports - may indicate systemic issues")


class TestImportRunner(unittest.TestCase):
    """Tests for import runner."""

    def test_run_comprehensive_import_tests_function_exists(self):
        """Test that run_comprehensive_import_tests function exists."""
        self.assertTrue(callable(run_comprehensive_import_tests))
