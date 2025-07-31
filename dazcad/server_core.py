"""Core server functionality for DazCAD."""

import sys
import unittest
import os
from io import StringIO

import cadquery as cq

# Import dependencies with fallback for direct execution
try:
    from .cadquery_processor import process_objects
    from .library_manager import LibraryManager
except ImportError:
    # Fallback for direct execution
    from cadquery_processor import process_objects
    from library_manager import LibraryManager

# Store for objects shown via show_object
shown_objects = []

# Initialize library manager with correct path to library files
# Use absolute path based on this file's location to ensure it works from any directory
current_dir = os.path.dirname(os.path.abspath(__file__))
library_path = os.path.join(current_dir, "library")
library_manager = LibraryManager(built_in_library_path=library_path)


def show_object(obj, name=None, color=None):
    """Capture objects to be displayed."""
    shown_objects.append({
        'object': obj,
        'name': name or f'Object_{len(shown_objects)}',
        'color': color
    })
    return obj


def run_tests_from_globals(exec_globals):
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



def run_cadquery_code(code):
    """Execute CadQuery code and return results."""
    # Clear previous shown objects
    shown_objects.clear()

    # Set up execution environment
    exec_globals = {
        'cq': cq,
        'cadquery': cq,
        'show_object': show_object,
        'show': show_object,  # Alias for compatibility
        '__name__': '__main__'
    }

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # Execute the code
        exec(code, exec_globals)  # pylint: disable=exec-used

        # Get output
        output = sys.stdout.getvalue()

        # Run tests if any exist
        test_results, test_output = run_tests_from_globals(exec_globals)

        # Process shown objects
        objects = process_objects(shown_objects)

        return {
            'success': True,
            'objects': objects,
            'output': output,
            'test_output': test_output,
            'test_results': test_results
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'output': sys.stdout.getvalue()
        }
    finally:
        sys.stdout = old_stdout


class TestServerCore(unittest.TestCase):
    """Unit tests for server core functionality."""

    def test_show_object(self):
        """Test show_object function."""
        # Clear any existing objects
        shown_objects.clear()

        # Create a test object
        box = cq.Workplane("XY").box(10, 10, 10)

        # Show it
        result = show_object(box, "TestBox", (1.0, 0.0, 0.0))

        # Verify it was stored
        self.assertEqual(len(shown_objects), 1)
        self.assertEqual(shown_objects[0]['name'], "TestBox")
        self.assertEqual(shown_objects[0]['color'], (1.0, 0.0, 0.0))
        self.assertEqual(result, box)

    def test_run_cadquery_code(self):
        """Test executing CadQuery code."""
        code = """
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
show_object(box, "MyBox")
print("Box created!")
"""
        result = run_cadquery_code(code)

        self.assertTrue(result['success'])
        self.assertEqual(len(result['objects']), 1)
        self.assertIn("Box created!", result['output'])

    def test_run_cadquery_code_with_error(self):
        """Test executing CadQuery code with error."""
        code = """
import cadquery as cq
# This will cause an error
undefined_variable
"""
        result = run_cadquery_code(code)

        self.assertFalse(result['success'])
        self.assertIn("undefined_variable", result['error'])
        self.assertIn("NameError", result['traceback'])

    def test_library_manager_initialization(self):
        """Test that library manager is properly initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))
        self.assertTrue(os.path.exists(library_manager.built_in_library_path))
