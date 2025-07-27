"""Core server functionality for DazCAD."""

import sys
import unittest
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

# Initialize library manager
library_manager = LibraryManager()


def show_object(obj, name=None, color=None):
    """Capture objects to be displayed."""
    shown_objects.append({
        'object': obj,
        'name': name or f'Object_{len(shown_objects)}',
        'color': color
    })
    return obj


def run_tests_from_globals(exec_globals):
    """Run tests found in the execution globals and return formatted results."""
    test_classes = []

    # Find all TestCase classes in the executed code
    for obj in exec_globals.values():
        if (isinstance(obj, type) and
            issubclass(obj, unittest.TestCase) and
            obj != unittest.TestCase):
            test_classes.append(obj)

    if not test_classes:
        return "No tests found.\n"

    test_results = []
    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        # Create a test suite for this class
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)

        # Run tests with custom result class to capture individual results
        class DetailedTestResult(unittest.TestResult):
            """Custom test result class to capture detailed test outcomes."""

            def __init__(self):
                super().__init__()
                self.test_results = []
                self.current_test = None

            def startTest(self, test):
                super().startTest(test)
                self.current_test = test

            def addSuccess(self, test):
                super().addSuccess(test)
                self.test_results.append((test, "PASS", None))

            def addError(self, test, err):
                super().addError(test, err)
                self.test_results.append((test, "ERROR", err))

            def addFailure(self, test, err):
                super().addFailure(test, err)
                self.test_results.append((test, "FAIL", err))

        # Run the tests
        result = DetailedTestResult()
        suite.run(result)

        # Format results for this test class
        class_name = test_class.__name__
        test_results.append(f"\n📋 {class_name}:")

        for test, status, error in result.test_results:
            total_tests += 1
            test_name = test._testMethodName  # pylint: disable=protected-access

            if status == "PASS":
                test_results.append(f"  ✅ {test_name}")
                passed_tests += 1
            elif status == "FAIL":
                test_results.append(f"  ❌ {test_name}")
                if error:
                    # Get just the assertion message, not full traceback
                    error_msg = str(error[1]).split('\n', maxsplit=1)[0]
                    test_results.append(f"     └─ {error_msg}")
            elif status == "ERROR":
                test_results.append(f"  💥 {test_name}")
                if error:
                    error_msg = str(error[1]).split('\n', maxsplit=1)[0]
                    test_results.append(f"     └─ {error_msg}")

    # Add summary
    summary = f"\n🧪 Test Summary: {passed_tests}/{total_tests} passed"
    if passed_tests == total_tests:
        summary += " 🎉"

    return summary + "\n" + "\n".join(test_results) + "\n"


def run_cadquery_code(code_str):
    """Execute CadQuery code and capture results"""
    global shown_objects  # pylint: disable=global-statement
    shown_objects = []

    # Import everything needed for exec environment
    # pylint: disable=import-outside-toplevel
    from cadquery import Color, Assembly, Location, Workplane, Vector
    import traceback
    # pylint: enable=import-outside-toplevel

    # Prepare execution environment
    exec_globals = {
        'cq': cq,
        'Color': Color,
        'Assembly': Assembly,
        'Location': Location,
        'Workplane': Workplane,
        'Vector': Vector,
        'show_object': show_object,
        'unittest': unittest,
        '__name__': '__main__'
    }

    # Capture stdout
    old_stdout = sys.stdout
    stdout_capture = StringIO()
    sys.stdout = stdout_capture

    try:
        # pylint: disable=exec-used
        exec(code_str, exec_globals)
        # pylint: enable=exec-used

        # Get the main execution output
        main_output = stdout_capture.getvalue()

        # Reset stdout capture for test output
        stdout_capture = StringIO()
        sys.stdout = stdout_capture

        # Run tests and get detailed results
        test_output = run_tests_from_globals(exec_globals)

        # Combine outputs
        combined_output = ""
        if main_output.strip():
            combined_output += main_output
        if test_output.strip() and test_output != "No tests found.\n":
            combined_output += "\n" + test_output

    except Exception as e:  # pylint: disable=broad-exception-caught
        combined_output = None
        # Get full traceback with line numbers
        error_traceback = traceback.format_exc()
        return {"success": False, "error": str(e),
                "traceback": error_traceback, "objects": []}
    finally:
        sys.stdout = old_stdout

    # Process shown objects
    result_objects = process_objects(shown_objects)

    return {"success": True, "objects": result_objects, "output": combined_output}


class TestServerCore(unittest.TestCase):
    """Tests for server core functionality."""

    def test_show_object(self):
        """Test the show_object function."""
        global shown_objects  # pylint: disable=global-statement
        shown_objects = []

        # Create a test object
        test_box = cq.Workplane("XY").box(10, 10, 10)
        result = show_object(test_box, name="TestBox", color="red")

        # Check that object was captured
        self.assertEqual(len(shown_objects), 1)
        self.assertEqual(shown_objects[0]['name'], "TestBox")
        self.assertEqual(shown_objects[0]['color'], "red")
        self.assertEqual(result, test_box)

    def test_run_cadquery_code(self):
        """Test running CadQuery code."""
        code = '''
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
show_object(box, name="test_box")
'''
        result = run_cadquery_code(code)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["objects"]), 1)
        self.assertIn("test_box", [obj["name"] for obj in result["objects"]])

    def test_library_manager_initialized(self):
        """Test that library manager is properly initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))
        self.assertTrue(hasattr(library_manager, 'get_file_content'))
        self.assertTrue(hasattr(library_manager, 'save_file'))
