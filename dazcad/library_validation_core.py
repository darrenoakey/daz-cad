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


def validate_cadquery_object(obj: Any) -> Tuple[bool, str]:
    """Validate that an object has valid CadQuery data.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not CADQUERY_AVAILABLE:
        return False, "CadQuery not available"

    try:
        if isinstance(obj, cq.Assembly):
            # Check assembly has parts
            if not obj.children:
                return False, "Assembly has no parts"
            # Verify we can get shapes from assembly
            shapes = obj.toCompound()
            if not shapes:
                return False, "Assembly compound is empty"
            return True, ""

        if hasattr(obj, 'val'):
            # CadQuery Workplane or Shape
            if hasattr(obj.val(), 'isNull') and obj.val().isNull():
                return False, "Shape is null"
            # Check if shape has geometry
            if hasattr(obj.val(), 'Vertices') and not obj.val().Vertices():
                return False, "Shape has no vertices"
            return True, ""

        if hasattr(obj, 'wrapped'):
            # Other CadQuery objects
            if hasattr(obj.wrapped, 'isNull') and obj.wrapped.isNull():
                return False, "Wrapped object is null"
            return True, ""

        return False, "Object is not a recognized CadQuery type"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, f"Validation error: {e}"


def validate_export_data(data: bytes, format_name: str) -> Tuple[bool, str]:
    """Validate exported data for a specific format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation
    if not isinstance(data, bytes):
        return False, f"Export did not return bytes, got {type(data).__name__}"

    if len(data) == 0:
        return False, "Export returned empty data"

    # Additional sanity check - verify it's not just whitespace
    if len(data.strip()) == 0:
        return False, "Export returned only whitespace"

    # Format-specific validation
    if format_name == 'stl':
        # STL files should start with "solid" or be binary
        if not (data.startswith(b'solid') or len(data) >= 84):
            return False, "Invalid STL format"
    elif format_name == 'step':
        # STEP files should contain ISO-10303
        if b'ISO-10303' not in data:
            return False, "Invalid STEP format - missing ISO-10303 header"
    elif format_name == '3mf':
        # 3MF files are ZIP archives starting with PK
        if not data.startswith(b'PK'):
            return False, "Invalid 3MF format - not a ZIP archive"

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

    def test_validate_export_data_stl(self):
        """Test STL format validation."""
        # Valid ASCII STL
        valid, error = validate_export_data(b'solid test\nendsolid', 'stl')
        self.assertTrue(valid)
        self.assertEqual(error, "")

        # Valid binary STL (at least 84 bytes)
        valid, error = validate_export_data(b'x' * 100, 'stl')
        self.assertTrue(valid)
        self.assertEqual(error, "")

        # Invalid STL
        valid, error = validate_export_data(b'invalid', 'stl')
        self.assertFalse(valid)
        self.assertEqual(error, "Invalid STL format")

    def test_validate_export_data_step(self):
        """Test STEP format validation."""
        # Valid STEP
        valid, error = validate_export_data(b'ISO-10303-21;', 'step')
        self.assertTrue(valid)
        self.assertEqual(error, "")

        # Invalid STEP
        valid, error = validate_export_data(b'invalid step', 'step')
        self.assertFalse(valid)
        self.assertIn("ISO-10303", error)

    def test_validate_export_data_3mf(self):
        """Test 3MF format validation."""
        # Valid 3MF (ZIP file)
        valid, error = validate_export_data(b'PK\x03\x04', '3mf')
        self.assertTrue(valid)
        self.assertEqual(error, "")

        # Invalid 3MF
        valid, error = validate_export_data(b'not a zip', '3mf')
        self.assertFalse(valid)
        self.assertIn("ZIP archive", error)

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
