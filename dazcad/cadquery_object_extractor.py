"""CadQuery object extraction functionality."""

import unittest
from typing import Dict, Any, List

try:
    from .library_validation_core import (is_exportable_object, get_object_type)
except ImportError:
    # Fallback for direct execution
    from library_validation_core import (is_exportable_object, get_object_type)


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


class TestCadQueryObjectExtractor(unittest.TestCase):
    """Tests for CadQuery object extractor."""

    def test_extract_exportable_objects_function_exists(self):
        """Test that extract_exportable_objects function exists."""
        self.assertTrue(callable(extract_exportable_objects))

    def test_extract_exportable_objects_empty(self):
        """Test extraction with empty results."""
        objects = extract_exportable_objects({})
        self.assertEqual(objects, [])

        objects = extract_exportable_objects({'shown_objects': [], 'globals': {}})
        self.assertEqual(objects, [])

    def test_extract_exportable_objects_with_mock_data(self):
        """Test extraction with mock data."""
        # Mock execution result
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
