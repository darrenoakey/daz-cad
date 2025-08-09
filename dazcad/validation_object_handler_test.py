"""Tests for object validation handler."""

import unittest

try:
    from .validation_object_handler import validate_single_object
except ImportError:
    # Fallback for direct execution
    from validation_object_handler import validate_single_object


class TestValidationObjectHandler(unittest.TestCase):
    """Tests for validation object handler."""

    def test_validate_single_object_with_empty_data(self):
        """Test validate_single_object with minimal test data."""
        # Real object info structure (without actual CadQuery object for simplicity)
        obj_info = {
            'object': None,  # No actual object, but real structure
            'name': 'TestObject',
            'type': 'workplane'
        }

        # Empty formats list
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
        self.assertEqual(result['name'], 'TestObject')
        self.assertEqual(result['type'], 'workplane')
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

    def test_validate_single_object_returns_consistent_counts(self):
        """Test that return counts are consistent with each other."""
        obj_info = {
            'object': None,
            'name': 'TestObject',
            'type': 'workplane'
        }

        supported_formats = []
        verbose = False

        result, test_count, success_count = validate_single_object(
            obj_info, supported_formats, verbose)

        # Success count should not exceed test count
        self.assertLessEqual(success_count, test_count)
        self.assertGreaterEqual(success_count, 0)
        self.assertGreaterEqual(test_count, 0)

    def test_validate_single_object_with_verbose_flag(self):
        """Test validate_single_object with verbose flag enabled."""
        obj_info = {
            'object': None,
            'name': 'TestObject',
            'type': 'workplane'
        }

        supported_formats = []
        verbose = True  # Enable verbose mode

        # Should handle verbose mode without crashing
        result, test_count, success_count = validate_single_object(
            obj_info, supported_formats, verbose)

        self.assertIsInstance(result, dict)
        self.assertIsInstance(test_count, int)
        self.assertIsInstance(success_count, int)

    def test_validate_single_object_with_assembly_type(self):
        """Test validate_single_object with assembly object type."""
        obj_info = {
            'object': None,
            'name': 'TestAssembly',
            'type': 'assembly'
        }

        class TestFormat:  # pylint: disable=too-few-public-methods
            """Test format class for validation testing."""
            def __init__(self, extension, assembly_handler=None):
                self.extension = extension
                self.assembly_handler = assembly_handler

        # Mix of formats with and without assembly support
        supported_formats = [
            TestFormat('stl'),  # No assembly handler
            TestFormat('3mf', assembly_handler=lambda x: x)  # Has assembly handler
        ]
        
        verbose = False

        result, test_count, success_count = validate_single_object(
            obj_info, supported_formats, verbose)

        self.assertIsInstance(result, dict)
        self.assertEqual(result['name'], 'TestAssembly')
        self.assertEqual(result['type'], 'assembly')


if __name__ == "__main__":
    unittest.main()
