"""Tests for CadQuery object extractor."""

import unittest

try:
    from .cadquery_object_extractor import extract_exportable_objects
except ImportError:
    # Fallback for direct execution
    from cadquery_object_extractor import extract_exportable_objects


class TestCadQueryObjectExtractor(unittest.TestCase):
    """Tests for CadQuery object extractor."""

    def test_extract_exportable_objects_empty_dict(self):
        """Test extraction with empty execution result."""
        objects = extract_exportable_objects({})
        self.assertEqual(objects, [])

    def test_extract_exportable_objects_empty_lists(self):
        """Test extraction with empty shown_objects and globals."""
        objects = extract_exportable_objects({'shown_objects': [], 'globals': {}})
        self.assertEqual(objects, [])

    def test_extract_exportable_objects_with_none_data(self):
        """Test extraction with test data containing None values."""
        # Test execution result with None objects
        execution_result = {
            'shown_objects': [
                {'object': None, 'name': 'TestObject', 'color': None}
            ],
            'globals': {
                'other_obj': None,
                'cq': None,  # Should be filtered out
                '__builtins__': None  # Should be filtered out
            }
        }

        # Should return empty list since None objects are not exportable
        objects = extract_exportable_objects(execution_result)
        self.assertEqual(objects, [])

    def test_extract_exportable_objects_filters_special_names(self):
        """Test that special names are filtered from globals."""
        execution_result = {
            'shown_objects': [],
            'globals': {
                'cq': 'some_value',
                'show_object': 'some_function',
                '__builtins__': 'builtins',
                '_private': 'private_value'
            }
        }
        
        objects = extract_exportable_objects(execution_result)
        self.assertEqual(objects, [])

    def test_extract_exportable_objects_returns_list(self):
        """Test that function always returns a list."""
        result = extract_exportable_objects({'shown_objects': [], 'globals': {}})
        self.assertIsInstance(result, list)

        result = extract_exportable_objects({})
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
