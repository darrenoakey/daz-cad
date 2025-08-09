"""Tests for CadQuery file executor."""

import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from .cadquery_file_executor import execute_cadquery_file, _import_cadquery


class TestCadQueryFileExecutor(unittest.TestCase):
    """Tests for CadQuery file executor."""

    def test_execute_cadquery_file_missing_file(self):
        """Test execution with missing file."""
        success, result, error = execute_cadquery_file(Path("nonexistent.py"))
        self.assertFalse(success)
        self.assertIn("Failed to read file", error)
        self.assertEqual(result, {})

    def test_execute_cadquery_file_simple_code(self):
        """Test execution with simple Python code."""
        # Create a temporary file with simple code
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("x = 1 + 1\nresult = x * 2")
            temp_file_path = Path(temp_file.name)

        try:
            success, result, error = execute_cadquery_file(temp_file_path)
            self.assertTrue(success)
            self.assertEqual(error, "")
            self.assertIn('globals', result)
            self.assertIn('shown_objects', result)
            # Check that our variables were created
            self.assertEqual(result['globals']['x'], 2)
            self.assertEqual(result['globals']['result'], 4)
        finally:
            # Clean up the temporary file
            temp_file_path.unlink()

    def test_execute_cadquery_file_with_show_object(self):
        """Test execution with show_object function."""
        # Create a temporary file that uses show_object
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("""
# Simple object to show
my_obj = "test_object"
show_object(my_obj, name="test_name", color="red")
""")
            temp_file_path = Path(temp_file.name)

        try:
            success, result, error = execute_cadquery_file(temp_file_path)
            self.assertTrue(success)
            self.assertEqual(error, "")
            self.assertIn('shown_objects', result)
            self.assertEqual(len(result['shown_objects']), 1)
            shown_obj = result['shown_objects'][0]
            self.assertEqual(shown_obj['object'], "test_object")
            self.assertEqual(shown_obj['name'], "test_name")
            self.assertEqual(shown_obj['color'], "red")
        finally:
            # Clean up the temporary file
            temp_file_path.unlink()

    def test_execute_cadquery_file_error_handling(self):
        """Test execution with code that raises an error."""
        # Create a temporary file with invalid code
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("raise ValueError('test error')")
            temp_file_path = Path(temp_file.name)

        try:
            success, result, error = execute_cadquery_file(temp_file_path)
            self.assertFalse(success)
            self.assertIn("Execution error: ValueError: test error", error)
            self.assertEqual(result, {})
        finally:
            # Clean up the temporary file
            temp_file_path.unlink()

    def test_import_cadquery_function(self):
        """Test the _import_cadquery function."""
        cq_module, available = _import_cadquery()
        # This should return either (cq, True) or (None, False)
        if available:
            self.assertIsNotNone(cq_module)
        else:
            self.assertIsNone(cq_module)
        self.assertIsInstance(available, bool)

    def test_import_cadquery_function_with_invalid_module(self):
        """Test the _import_cadquery function with non-existent module."""
        cq_module, available = _import_cadquery("nonexistent_module_12345")
        # Should return (None, False) for non-existent module
        self.assertIsNone(cq_module)
        self.assertFalse(available)

    def test_import_cadquery_function_with_valid_module(self):
        """Test the _import_cadquery function with existing module."""
        cq_module, available = _import_cadquery("sys")
        # Should return (None, True) for existing module that's not cadquery
        self.assertIsNone(cq_module)
        self.assertTrue(available)


if __name__ == '__main__':
    unittest.main()
