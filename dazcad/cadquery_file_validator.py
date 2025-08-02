"""Core validation function for CadQuery library files.

This module contains the main validation function that tests a CadQuery file
for execution, object validation, and export compatibility.
"""

import unittest
from pathlib import Path
from typing import Dict, Any

# Import common patterns to reduce duplication
try:
    from .common_imports import CADQUERY_AVAILABLE
    from .validation_patterns import (
        create_validation_result_template, check_common_validation_assertions
    )
    from .test_cadquery_file import (execute_cadquery_file, extract_exportable_objects)
    from .export_utils import get_supported_export_formats
    from .validation_object_handler import validate_single_object
except ImportError:
    # Fallback for direct execution
    from common_imports import CADQUERY_AVAILABLE
    from validation_patterns import (
        create_validation_result_template, check_common_validation_assertions
    )
    from test_cadquery_file import (execute_cadquery_file, extract_exportable_objects)
    from export_utils import get_supported_export_formats
    from validation_object_handler import validate_single_object


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
    result = create_validation_result_template()
    result['file'] = file_path.name

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
    supported_formats = (list(get_supported_export_formats().values())
                        if CADQUERY_AVAILABLE else [])

    # Validate each object
    for obj_info in exportable_objects:
        obj_result, test_count, success_count = validate_single_object(
            obj_info, supported_formats, verbose)

        if obj_result['valid']:
            result['summary']['valid_objects'] += 1

        result['summary']['total_export_tests'] += test_count
        result['summary']['successful_exports'] += success_count
        result['objects'].append(obj_result)

    # Check if all exports were successful
    summary = result['summary']
    if (summary['valid_objects'] < summary['total_objects'] or
        summary['successful_exports'] < summary['total_export_tests']):
        result['success'] = False

    if verbose and result['success']:
        msg = (f"✅ {file_path.name}: All {summary['total_objects']} objects "
               f"valid, {summary['successful_exports']} exports successful")
        print(msg)

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

        # Use common validation assertions
        check_common_validation_assertions(self, result)
