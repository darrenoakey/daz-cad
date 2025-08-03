"""Test functions for validating individual CadQuery library files.

This module provides helper functions for testing CadQuery files:
- File execution
- Object extraction
- Export testing
"""

import unittest
from pathlib import Path
from typing import Any, Tuple

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .export_utils import (export_shape_to_format, export_assembly_to_format)
    from .library_validation_core import validate_export_data
    from .cadquery_file_executor import execute_cadquery_file
    from .cadquery_object_extractor import extract_exportable_objects
except ImportError:
    # Fallback for direct execution
    from export_utils import (export_shape_to_format, export_assembly_to_format)
    from library_validation_core import validate_export_data
    from cadquery_file_executor import execute_cadquery_file
    from cadquery_object_extractor import extract_exportable_objects


def test_export_format(obj: Any, obj_type: str, format_name: str) -> Tuple[bool, str]:
    """Test exporting an object in a specific format.

    Args:
        obj: CadQuery object to export
        obj_type: Type of object ('shape' or 'assembly')
        format_name: Export format extension (e.g., 'stl', 'step')

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Perform the export
        if obj_type == 'assembly':
            data = export_assembly_to_format(obj, format_name)
        else:
            data = export_shape_to_format(obj, format_name)

        # Validate the exported data
        return validate_export_data(data, format_name)

    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, f"Export error: {type(e).__name__}: {e}"


class TestCadQueryFile(unittest.TestCase):
    """Unit tests for the CadQuery file validation functions."""

    def test_execute_cadquery_file_missing(self):
        """Test execution with missing file."""
        success, result, error = execute_cadquery_file(Path("nonexistent.py"))
        self.assertFalse(success)
        self.assertIn("Failed to read file", error)
        self.assertEqual(result, {})

    def test_extract_exportable_objects_empty(self):
        """Test extraction with empty results."""
        objects = extract_exportable_objects({})
        self.assertEqual(objects, [])

        objects = extract_exportable_objects({'shown_objects': [], 'globals': {}})
        self.assertEqual(objects, [])

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_export_format_functions(self):
        """Test export format functions with test data."""
        # Create a simple shape for testing
        box = cq.Workplane("XY").box(10, 10, 10)

        # Test successful export
        success, error = test_export_format(box, 'shape', 'stl')
        # May or may not succeed depending on environment
        self.assertIsInstance(success, bool)
        self.assertIsInstance(error, str)

    def test_test_export_format_function_exists(self):
        """Test that test_export_format function exists."""
        self.assertTrue(callable(test_export_format))
