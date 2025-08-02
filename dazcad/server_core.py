"""Core server functionality for DazCAD."""

import os
import sys
import traceback
import unittest
from io import StringIO

import cadquery as cq

# Import dependencies with fallback for direct execution
try:
    from .cadquery_processor import process_objects
    from .library_manager import LibraryManager
    from .colored_logging import log_debug, log_success, log_error, log_library_operation
    from .server_test_runner import run_tests_from_globals
except ImportError:
    # Fallback for direct execution
    from cadquery_processor import process_objects
    from library_manager import LibraryManager
    from colored_logging import log_debug, log_success, log_error, log_library_operation
    from server_test_runner import run_tests_from_globals

# Store for objects shown via show_object
shown_objects = []

# Initialize library manager with correct path to library files
# Use absolute path based on this file's location to ensure it works from any directory
current_dir = os.path.dirname(os.path.abspath(__file__))
library_path = os.path.join(current_dir, "library")

log_library_operation("STARTUP", "Server core initializing")
log_library_operation("STARTUP", f"Current directory: {current_dir}")
log_library_operation("STARTUP", f"Looking for library at: {library_path}")
log_library_operation("STARTUP", f"Library path exists: {os.path.exists(library_path)}")

# List what's actually in the current directory for debugging
try:
    current_contents = os.listdir(current_dir)
    log_debug("STARTUP", f"Current directory contents: {current_contents}")

    # Also check if there's a library subdirectory
    if 'library' in current_contents:
        library_contents = os.listdir(library_path)
        log_debug("STARTUP", f"Library directory contents: {library_contents}")

        # Count .py files
        py_files = [f for f in library_contents if f.endswith('.py') and not f.startswith('__')]
        log_library_operation("STARTUP",
                            f"Found {len(py_files)} Python files in library: {py_files}")
except Exception as e:  # pylint: disable=broad-exception-caught
    log_error("STARTUP", f"Error listing directories: {e}")

library_manager = LibraryManager(built_in_library_path=library_path)


def show_object(obj, name=None, color=None):
    """Capture objects to be displayed."""
    shown_objects.append({
        'object': obj,
        'name': name or f'Object_{len(shown_objects)}',
        'color': color
    })
    return obj


def run_cadquery_code(code):
    """Execute CadQuery code and return results."""
    log_debug("CODE_EXEC", f"Starting execution of {len(code)} characters of code")

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
        log_debug("CODE_EXEC", "Executing code...")

        # Execute the code
        exec(code, exec_globals)  # pylint: disable=exec-used

        # Get output
        output = sys.stdout.getvalue()
        log_success("CODE_EXEC",
                   f"Code executed successfully, {len(shown_objects)} objects created")

        # Run tests if any exist
        test_results, test_output = run_tests_from_globals(exec_globals)

        # Process shown objects
        log_debug("CODE_EXEC", f"Processing {len(shown_objects)} shown objects...")
        objects = process_objects(shown_objects)
        log_success("CODE_EXEC",
                   f"Successfully processed {len(objects)} objects for visualization")

        return {
            'success': True,
            'objects': objects,
            'output': output,
            'test_output': test_output,
            'test_results': test_results
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        log_error("CODE_EXEC", f"Code execution failed: {error_msg}")
        log_debug("CODE_EXEC", f"Full traceback: {error_traceback}")

        return {
            'success': False,
            'error': error_msg,
            'traceback': error_traceback,
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
