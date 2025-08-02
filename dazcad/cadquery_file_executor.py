"""CadQuery file execution functionality."""

import unittest
from pathlib import Path
from typing import Dict, Any, Tuple

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False


def execute_cadquery_file(file_path: Path) -> Tuple[bool, Dict[str, Any], str]:
    """Execute a CadQuery file and capture results.

    Args:
        file_path: Path to the CadQuery Python file

    Returns:
        Tuple of (success, result_dict, error_message)
        result_dict contains 'shown_objects' and 'globals'
    """
    # Read the file content
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            code = file.read()
    except IOError as e:
        return False, {}, f"Failed to read file: {e}"

    # Set up execution environment
    shown_objects = []

    def show_object(obj, name=None, color=None):
        """Capture objects to be displayed."""
        shown_objects.append({
            'object': obj,
            'name': name or f'Object_{len(shown_objects)}',
            'color': color
        })
        return obj

    # Execute the code
    exec_globals = {
        '__name__': '__main__',
        'show_object': show_object,
        'cq': cq if CADQUERY_AVAILABLE else None
    }

    try:
        exec(code, exec_globals)  # pylint: disable=exec-used
        return True, {'shown_objects': shown_objects, 'globals': exec_globals}, ""
    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, {}, f"Execution error: {type(e).__name__}: {e}"


class TestCadQueryFileExecutor(unittest.TestCase):
    """Tests for CadQuery file executor."""

    def test_execute_cadquery_file_function_exists(self):
        """Test that execute_cadquery_file function exists."""
        self.assertTrue(callable(execute_cadquery_file))

    def test_execute_cadquery_file_missing_file(self):
        """Test execution with missing file."""
        success, result, error = execute_cadquery_file(Path("nonexistent.py"))
        self.assertFalse(success)
        self.assertIn("Failed to read file", error)
        self.assertEqual(result, {})
