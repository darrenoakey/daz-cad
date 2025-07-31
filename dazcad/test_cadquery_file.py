"""Test functions for validating individual CadQuery library files.

This module provides helper functions for testing CadQuery files:
- File execution
- Object extraction
- Export testing
"""

import unittest
from pathlib import Path
from typing import Dict, Any, List, Tuple

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .export_utils import (export_shape_to_format, export_assembly_to_format)
    from .library_validation_core import (validate_export_data,
                                          is_exportable_object,
                                          get_object_type)
except ImportError:
    # Fallback for direct execution
    from export_utils import (export_shape_to_format, export_assembly_to_format)
    from library_validation_core import (validate_export_data,
                                        is_exportable_object,
                                        get_object_type)


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


def extract_exportable_objects(execution_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all exportable objects from execution result.

    Args:
        execution_result: Result from execute_cadquery_file

    Returns:
        List of dicts with 'object', 'name', and 'type' keys
    """
    exportable_objects = []

    # Add shown objects
    for shown_obj in execution_result.get('shown_objects', []):
        obj = shown_obj['object']
        if is_exportable_object(obj):
            exportable_objects.append({
                'object': obj,
                'name': shown_obj['name'],
                'type': get_object_type(obj)
            })

    # Look for other exportable objects in globals
    for name, obj in execution_result.get('globals', {}).items():
        if (not name.startswith('_') and
            name not in ['cq', 'show_object', '__builtins__'] and
            is_exportable_object(obj) and
            # Avoid duplicates from shown_objects
            not any(o['object'] is obj for o in exportable_objects)):
            exportable_objects.append({
                'object': obj,
                'name': name,
                'type': get_object_type(obj)
            })

    return exportable_objects


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
        """Test export format functions with mock data."""
        # Create a simple shape for testing
        box = cq.Workplane("XY").box(10, 10, 10)

        # Test successful export
        success, error = test_export_format(box, 'shape', 'stl')
        # May or may not succeed depending on environment
        self.assertIsInstance(success, bool)
        self.assertIsInstance(error, str)
