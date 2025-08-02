"""Test runner for server code execution."""

import unittest
from io import StringIO


def run_tests_from_globals(exec_globals):  # pylint: disable=too-many-locals,too-many-branches
    """Run tests found in the execution globals and return results."""
    test_results = []
    test_output = StringIO()

    # Find all test classes
    test_classes = []
    for _, obj in exec_globals.items():
        if (isinstance(obj, type) and
            issubclass(obj, unittest.TestCase) and
            obj is not unittest.TestCase):
            test_classes.append(obj)

    if not test_classes:
        return test_results, test_output.getvalue()

    # Create test suite
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests and capture results
    runner = unittest.TextTestRunner(stream=test_output, verbosity=2)
    result = runner.run(suite)

    # Format results
    for test_class in test_classes:
        class_result = {
            'name': test_class.__name__,
            'tests': [],
            'passed': 0,
            'failed': 0
        }

        # Get test methods
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                test_id = f"{test_class.__name__}.{method_name}"

                # Check if test passed
                passed = True
                error_msg = None

                # Check failures
                for failure in result.failures:
                    if failure[0].id() == test_id:
                        passed = False
                        error_msg = failure[1]
                        break

                # Check errors
                for error in result.errors:
                    if error[0].id() == test_id:
                        passed = False
                        error_msg = error[1]
                        break

                class_result['tests'].append({
                    'name': method_name,
                    'passed': passed,
                    'error': error_msg
                })

                if passed:
                    class_result['passed'] += 1
                else:
                    class_result['failed'] += 1

        test_results.append(class_result)

    return test_results, test_output.getvalue()


class TestServerTestRunner(unittest.TestCase):
    """Tests for server test runner."""

    def test_run_tests_from_globals_with_no_tests(self):
        """Test running tests when no test classes exist."""
        test_globals = {'some_var': 42}
        test_results, test_output = run_tests_from_globals(test_globals)

        self.assertEqual(test_results, [])
        self.assertEqual(test_output, "")

    def test_run_tests_from_globals_function_exists(self):
        """Test that run_tests_from_globals function exists."""
        self.assertTrue(callable(run_tests_from_globals))
