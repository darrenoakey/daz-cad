"""Unit tests for export utilities."""

import base64
import unittest
from unittest.mock import Mock

try:
    from .export_utils import (
        ExportFormat, get_format_by_name,
        export_shape_to_stl, export_shape_to_format, export_assembly_to_format,
        get_supported_formats, get_supported_export_formats
    )
except ImportError:
    from export_utils import (
        ExportFormat, get_format_by_name,
        export_shape_to_stl, export_shape_to_format, export_assembly_to_format,
        get_supported_formats, get_supported_export_formats
    )


class TestExportFunctions(unittest.TestCase):
    """Test the export utility functions."""

    def test_export_format_structure(self):
        """Test that export format structure is correct."""
        # Create a format with the actual constructor
        fmt = ExportFormat(
            extension="stl",
            mime_type="model/stl",
            description="STL 3D Model",
            supports_colors=False
        )

        # Test attributes
        self.assertEqual(fmt.name, "STL")
        self.assertEqual(fmt.extension, "stl")
        self.assertEqual(fmt.mime_type, "model/stl")
        self.assertFalse(fmt.supports_colors)
        self.assertIsNone(fmt.assembly_handler)

    def test_export_format_methods(self):
        """Test ExportFormat methods."""
        # Test without assembly handler
        fmt = ExportFormat("stl", "model/stl", "STL 3D Model")
        self.assertFalse(fmt.supports_assemblies())

        # Test with assembly handler
        fmt.set_assembly_handler(lambda a: b"assembly data")
        self.assertTrue(fmt.supports_assemblies())

    def test_get_format_by_name(self):
        """Test getting format by name."""
        # Test valid formats
        stl = get_format_by_name('stl')
        self.assertIsNotNone(stl)
        self.assertEqual(stl.name, 'STL')

        # Test case insensitive
        step = get_format_by_name('STEP')
        self.assertIsNotNone(step)
        self.assertEqual(step.extension, 'step')

    def test_export_shape_to_stl(self):
        """Test STL export functionality."""
        # Mock shape object that returns a mock when toSTL() is called
        mock_shape = Mock()
        mock_shape.toSTL.return_value = "mock stl data"

        # Export to STL
        stl_data = export_shape_to_stl(mock_shape)

        # Verify export was called
        mock_shape.toSTL.assert_called_once()

        # Should return base64-encoded string
        self.assertIsInstance(stl_data, str)

        # Should be valid base64
        try:
            decoded = base64.b64decode(stl_data)
            self.assertIsInstance(decoded, bytes)
        except ValueError as e:
            self.fail(f"Invalid base64 string: {e}")

    def test_export_shape_to_format(self):
        """Test shape export to different formats."""
        # Mock shape that returns string content
        mock_shape = Mock()
        mock_shape.toSTL.return_value = "mock stl data"

        # Test STL export
        stl_data = export_shape_to_format(mock_shape, 'stl')
        self.assertIsInstance(stl_data, bytes)

    def test_export_assembly_to_format(self):
        """Test assembly export to different formats."""
        # Mock assembly with compound conversion
        mock_assembly = Mock()
        mock_compound = Mock()
        mock_assembly.toCompound.return_value = mock_compound
        mock_compound.toSTEP.return_value = "mock step data"

        # Test that export_assembly_to_format works with step format
        result = export_assembly_to_format(mock_assembly, 'step')
        self.assertIsInstance(result, bytes)

    def test_get_supported_formats(self):
        """Test that supported formats function works."""
        formats = get_supported_formats()
        self.assertIsInstance(formats, list)
        self.assertTrue(len(formats) > 0)
        self.assertIn('stl', formats)
        self.assertIn('step', formats)

    def test_get_supported_export_formats(self):
        """Test getting export formats as dictionary."""
        formats = get_supported_export_formats()
        self.assertIsInstance(formats, dict)
        self.assertIn('stl', formats)
        self.assertIn('step', formats)
        # Test that values are ExportFormat objects
        self.assertIsInstance(formats['stl'], ExportFormat)
