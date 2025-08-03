"""Object validation handler for CadQuery library files."""

import unittest

try:
    from .test_cadquery_file import test_export_format
    from .library_validation_core import validate_cadquery_object
except ImportError:
    # Fallback for direct execution
    from test_cadquery_file import test_export_format
    from library_validation_core import validate_cadquery_object


def validate_single_object(obj_info, supported_formats, verbose):
    """Validate a single object and test its exports.

    Args:
        obj_info: Dictionary with object information
        supported_formats: List of supported export formats
        verbose: Whether to print verbose output

    Returns:
        Tuple of (obj_result dict, export_test_count, successful_export_count)
    """
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

    export_test_count = 0
    successful_export_count = 0

    if obj_valid:
        # Test exports for valid objects
        for export_format in supported_formats:
            format_name = export_format.extension

            # Skip formats that don't support assemblies
            if (obj_type == 'assembly' and
                export_format.assembly_handler is None):
                continue

            export_test_count += 1

            export_success, export_error = test_export_format(
                obj, obj_type, format_name)

            obj_result['exports'][format_name] = {
                'success': export_success,
                'error': export_error
            }

            if export_success:
                successful_export_count += 1
            elif verbose:
                print(f"  ❌ {obj_name} -> {format_name}: {export_error}")
    elif verbose:
        print(f"  ❌ {obj_name}: Invalid object - {obj_error}")

    return obj_result, export_test_count, successful_export_count


class TestValidationObjectHandler(unittest.TestCase):
    """Tests for validation object handler."""

    def test_validate_single_object_function_exists(self):
        """Test that validate_single_object function exists."""
        self.assertTrue(callable(validate_single_object))

    def test_validate_single_object_with_test_data(self):
        """Test validate_single_object with real test data structure."""
        # Real object info structure (without actual CadQuery object for simplicity)
        obj_info = {
            'object': None,  # No actual object, but real structure
            'name': 'TestObject',
            'type': 'workplane'
        }

        # Real formats (empty list for test)
        supported_formats = []
        verbose = False

        # Should not crash and return proper structure
        result, test_count, success_count = validate_single_object(
            obj_info, supported_formats, verbose)

        self.assertIsInstance(result, dict)
        self.assertIn('name', result)
        self.assertIn('type', result)
        self.assertIn('valid', result)
        self.assertIn('error', result)
        self.assertIn('exports', result)
        self.assertIsInstance(test_count, int)
        self.assertIsInstance(success_count, int)

    def test_validate_single_object_with_formats(self):
        """Test validate_single_object with format structures."""
        # Real object info structure
        obj_info = {
            'object': None,
            'name': 'TestObject',
            'type': 'workplane'
        }

        # Create format-like structures for testing
        class TestFormat:  # pylint: disable=too-few-public-methods
            """Test format class for validation testing."""
            def __init__(self, extension, assembly_handler=None):
                self.extension = extension
                self.assembly_handler = assembly_handler

        # Test with some real format structures
        supported_formats = [
            TestFormat('stl'),
            TestFormat('step'),
            TestFormat('3mf', assembly_handler=lambda x: x)
        ]
        
        verbose = False

        # Should handle the format structures correctly
        result, test_count, success_count = validate_single_object(
            obj_info, supported_formats, verbose)

        self.assertIsInstance(result, dict)
        self.assertIn('exports', result)
        self.assertIsInstance(result['exports'], dict)
        self.assertIsInstance(test_count, int)
        self.assertIsInstance(success_count, int)
