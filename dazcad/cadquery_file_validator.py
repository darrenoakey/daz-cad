"""Core validation function for CadQuery library files.

This module contains the main validation function that tests a CadQuery file
for execution, object validation, and export compatibility.
"""

import unittest
from pathlib import Path
from typing import Dict, Any

try:
    from .test_cadquery_file import (execute_cadquery_file,
                                     extract_exportable_objects,
                                     test_export_format)
    from .export_utils import get_supported_export_formats
    from .library_validation_core import validate_cadquery_object
except ImportError:
    # Fallback for direct execution
    from test_cadquery_file import (execute_cadquery_file,
                                   extract_exportable_objects,
                                   test_export_format)
    from export_utils import get_supported_export_formats
    from library_validation_core import validate_cadquery_object


def validate_cadquery_file(file_path: Path, verbose: bool = False) -> Dict[str, Any]:
    """Perform comprehensive validation of a CadQuery library file.

    This is the main function that should be called to validate a library file.
    It executes the file, validates all objects, and tests all export formats.

    Args:
        file_path: Path to the CadQuery Python file
        verbose: If True, print detailed results during testing

    Returns:
        Dictionary with validation results including:
        - success: bool - Overall success status
        - file: str - Filename
        - execution_error: str - Error message if execution failed
        - objects: list - Validation results for each object
        - summary: dict - Summary statistics
    """
    result = {
        'success': True,
        'file': file_path.name,
        'execution_error': '',
        'objects': [],
        'summary': {
            'total_objects': 0,
            'valid_objects': 0,
            'total_export_tests': 0,
            'successful_exports': 0
        }
    }

    # Execute the file
    exec_success, exec_result, exec_error = execute_cadquery_file(file_path)
    if not exec_success:
        result['success'] = False
        result['execution_error'] = exec_error
        if verbose:
            print(f"❌ {file_path.name}: {exec_error}")
        return result

    # Get exportable objects
    exportable_objects = extract_exportable_objects(exec_result)
    if not exportable_objects:
        result['success'] = False
        result['execution_error'] = "No exportable objects found"
        if verbose:
            print(f"❌ {file_path.name}: No exportable objects found")
        return result

    result['summary']['total_objects'] = len(exportable_objects)

    # Get supported export formats
    try:
        import cadquery  # pylint: disable=unused-import
        cadquery_available = True
    except ImportError:
        cadquery_available = False

    supported_formats = (list(get_supported_export_formats().values())
                        if cadquery_available else [])

    # Validate each object
    for obj_info in exportable_objects:
        obj = obj_info['object']
        obj_name = obj_info['name']
        obj_type = obj_info['type']

        # Validate object structure
        obj_valid, obj_error = validate_cadquery_object(obj)
        obj_result = {
            'name': obj_name,
            'type': obj_type,
            'valid': obj_valid,
            'error': obj_error,
            'exports': {}
        }

        if obj_valid:
            result['summary']['valid_objects'] += 1

            # Test exports for valid objects
            for export_format in supported_formats:
                format_name = export_format.extension

                # Skip formats that don't support assemblies
                if (obj_type == 'assembly' and
                    export_format.assembly_handler is None):
                    continue

                result['summary']['total_export_tests'] += 1

                export_success, export_error = test_export_format(
                    obj, obj_type, format_name)

                obj_result['exports'][format_name] = {
                    'success': export_success,
                    'error': export_error
                }

                if export_success:
                    result['summary']['successful_exports'] += 1
                else:
                    if verbose:
                        print(f"  ❌ {obj_name} -> {format_name}: {export_error}")
        else:
            if verbose:
                print(f"  ❌ {obj_name}: Invalid object - {obj_error}")

        result['objects'].append(obj_result)

    # Check if all exports were successful
    if (result['summary']['valid_objects'] < result['summary']['total_objects'] or
        result['summary']['successful_exports'] < result['summary']['total_export_tests']):
        result['success'] = False

    if verbose and result['success']:
        print(f"✅ {file_path.name}: All {result['summary']['total_objects']} objects "
              f"valid, {result['summary']['successful_exports']} exports successful")

    return result


class TestCadQueryFileValidator(unittest.TestCase):
    """Unit tests for the CadQuery file validator."""

    def test_validate_cadquery_file_missing(self):
        """Test validation with missing file."""
        result = validate_cadquery_file(Path("nonexistent.py"))
        self.assertFalse(result['success'])
        self.assertIn("Failed to read file", result['execution_error'])

    def test_validate_cadquery_file_structure(self):
        """Test that validation returns correct structure."""
        result = validate_cadquery_file(Path("nonexistent.py"))

        # Check all required keys exist
        self.assertIn('success', result)
        self.assertIn('file', result)
        self.assertIn('execution_error', result)
        self.assertIn('objects', result)
        self.assertIn('summary', result)

        # Check summary structure
        summary = result['summary']
        self.assertIn('total_objects', summary)
        self.assertIn('valid_objects', summary)
        self.assertIn('total_export_tests', summary)
        self.assertIn('successful_exports', summary)
