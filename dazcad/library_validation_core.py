"""Core validation logic for library files.

This module contains the core validation functions for CadQuery library files.
"""

import unittest
from typing import Any, Tuple

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

# Import format validators
try:
    from .library_validation_formats import validate_export_data
except ImportError:
    from library_validation_formats import validate_export_data


def validate_cadquery_object(obj: Any) -> Tuple[bool, str]:
    """Validate that an object has valid CadQuery data.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not CADQUERY_AVAILABLE:
        return False, "CadQuery not available"

    try:
        # Check if object is an assembly
        if isinstance(obj, cq.Assembly):
            return _validate_assembly(obj)

        # Check if object has val() method (Workplane or Shape)
        if hasattr(obj, 'val'):
            return _validate_workplane_or_shape(obj)

        # Check if object has wrapped attribute (other CadQuery objects)
        if hasattr(obj, 'wrapped'):
            return _validate_wrapped_object(obj)

        return False, "Object is not a recognized CadQuery type"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, f"Validation error: {e}"


def _validate_assembly(assembly: Any) -> Tuple[bool, str]:
    """Validate a CadQuery assembly."""
    if not assembly.children:
        return False, "Assembly has no parts"

    shapes = assembly.toCompound()
    if not shapes:
        return False, "Assembly compound is empty"

    return True, ""


def _validate_workplane_or_shape(obj: Any) -> Tuple[bool, str]:
    """Validate a CadQuery Workplane or Shape."""
    shape_val = obj.val()

    if hasattr(shape_val, 'isNull') and shape_val.isNull():
        return False, "Shape is null"

    if hasattr(shape_val, 'Vertices') and not shape_val.Vertices():
        return False, "Shape has no vertices"

    return True, ""


def _validate_wrapped_object(obj: Any) -> Tuple[bool, str]:
    """Validate a wrapped CadQuery object."""
    if hasattr(obj.wrapped, 'isNull') and obj.wrapped.isNull():
        return False, "Wrapped object is null"

    return True, ""


def is_exportable_object(obj: Any) -> bool:
    """Check if an object can be exported."""
    if not CADQUERY_AVAILABLE:
        return False

    return (hasattr(obj, 'val') or  # CadQuery Workplane/Shape
            isinstance(obj, cq.Assembly) or  # CadQuery Assembly
            hasattr(obj, 'wrapped'))  # Other CadQuery objects


def get_object_type(obj: Any) -> str:
    """Determine the type of an exportable object."""
    if not CADQUERY_AVAILABLE:
        return 'unknown'

    if isinstance(obj, cq.Assembly):
        return 'assembly'
    return 'shape'


class TestLibraryValidationCore(unittest.TestCase):
    """Tests for library validation core functionality."""

    def test_validate_export_data_empty(self):
        """Test validation with empty data."""
        valid, error = validate_export_data(b'', 'stl')
        self.assertFalse(valid)
        self.assertEqual(error, "Export returned empty data")

    def test_validate_export_data_whitespace(self):
        """Test validation with whitespace only."""
        valid, error = validate_export_data(b'   \n\t  ', 'stl')
        self.assertFalse(valid)
        self.assertEqual(error, "Export returned only whitespace")

    def test_validate_export_data_not_bytes(self):
        """Test validation with non-bytes data."""
        valid, error = validate_export_data("not bytes", 'stl')  # type: ignore
        self.assertFalse(valid)
        self.assertIn("Export did not return bytes", error)

    def test_is_exportable_object(self):
        """Test exportable object detection."""
        # Without CadQuery available
        self.assertFalse(is_exportable_object(None))
        self.assertFalse(is_exportable_object("string"))
        self.assertFalse(is_exportable_object(42))

    def test_get_object_type(self):
        """Test object type detection."""
        # Without specific object
        self.assertIn(get_object_type(None), ['unknown', 'shape'])

    def test_validate_cadquery_object_without_cq(self):
        """Test validation when CadQuery is not available."""
        if not CADQUERY_AVAILABLE:
            valid, error = validate_cadquery_object(None)
            self.assertFalse(valid)
            self.assertEqual(error, "CadQuery not available")
