"""Export functionality for CadQuery objects."""

import base64
import os
import tempfile
import unittest

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False


def export_shape_to_stl(shape):
    """Export a CadQuery shape to STL format as base64 string.

    Args:
        shape: A CadQuery Workplane or Shape object

    Returns:
        Base64 encoded STL data
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # Create a temporary file for STL export
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        # Export to STL file
        cq.exporters.export(shape, temp_filename, cq.exporters.ExportTypes.STL)

        # Read the STL file back as binary data
        with open(temp_filename, 'rb') as stl_file:
            stl_bytes = stl_file.read()

        # Encode as base64
        return base64.b64encode(stl_bytes).decode('utf-8')

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


def export_assembly_to_format(assembly, export_format):
    """Export a CadQuery assembly to specified format as binary data.

    Args:
        assembly: A CadQuery Assembly object
        export_format: Export format ('stl', 'step') - 3MF not supported by assembly.save()

    Returns:
        Binary data of the exported file
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # For assemblies, we use the save method - only STL and STEP are confirmed working
    format_map = {
        'stl': ('.stl', cq.exporters.ExportTypes.STL),
        'step': ('.step', cq.exporters.ExportTypes.STEP)
    }

    if export_format not in format_map:
        raise ValueError(f"Unsupported assembly format: {export_format}")

    extension, export_type = format_map[export_format]

    # Create a temporary file for export
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        # Use assembly.save() method for assemblies
        assembly.save(temp_filename, export_type)

        # Read the file back as binary data
        with open(temp_filename, 'rb') as exported_file:
            return exported_file.read()

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


def export_shape_to_format(shape, export_format):
    """Export a CadQuery shape to specified format as binary data.

    Args:
        shape: A CadQuery Workplane or Shape object
        export_format: Export format ('stl', 'step', '3mf')

    Returns:
        Binary data of the exported file
    """
    if not CADQUERY_AVAILABLE:
        raise ImportError("CadQuery not available")

    # Get file extension and export type - check if format is available
    format_map = {
        'stl': ('.stl', cq.exporters.ExportTypes.STL),
        'step': ('.step', cq.exporters.ExportTypes.STEP)
    }

    # Check if 3MF is available in this CadQuery version
    if hasattr(cq.exporters.ExportTypes, 'THREEMF'):
        format_map['3mf'] = ('.3mf', cq.exporters.ExportTypes.THREEMF)

    if export_format not in format_map:
        available_formats = ', '.join(format_map.keys())
        raise ValueError(f"Unsupported format: {export_format}. "
                        f"Available formats: {available_formats}")

    extension, export_type = format_map[export_format]

    # Create a temporary file for export
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        temp_filename = temp_file.name

    try:
        # Export shape to file
        cq.exporters.export(shape, temp_filename, export_type)

        # Read the file back as binary data
        with open(temp_filename, 'rb') as exported_file:
            return exported_file.read()

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


def get_supported_formats():
    """Get list of supported export formats based on CadQuery capabilities.

    Returns:
        List of supported format strings
    """
    if not CADQUERY_AVAILABLE:
        return []

    formats = ['stl', 'step']

    # Check if 3MF is available in this CadQuery version
    if hasattr(cq.exporters.ExportTypes, 'THREEMF'):
        formats.append('3mf')

    return formats


class TestExportFunctions(unittest.TestCase):
    """Unit tests for export functionality."""

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_export_shape_to_stl(self):
        """Test STL export functionality."""
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Export it
        stl_data = export_shape_to_stl(box)

        # Should be valid base64
        self.assertIsInstance(stl_data, str)
        self.assertGreater(len(stl_data), 0)

        # Should decode without error
        decoded = base64.b64decode(stl_data)
        self.assertGreater(len(decoded), 0)

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_export_shape_to_format(self):
        """Test shape export to different formats."""
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Test each supported format (dynamically determined)
        supported_formats = get_supported_formats()
        for fmt in supported_formats:
            with self.subTest(format=fmt):
                data = export_shape_to_format(box, fmt)
                self.assertIsInstance(data, bytes)
                self.assertGreater(len(data), 0)

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_export_assembly_to_format(self):
        """Test assembly export to different formats."""
        # Create a simple assembly
        assembly = cq.Assembly()
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 5)
        assembly.add(box1, name="Box1", color=cq.Color("red"))
        assembly.add(box2, name="Box2", color=cq.Color("green"))

        # Test only assembly-supported formats (STL and STEP)
        for fmt in ['stl', 'step']:
            with self.subTest(format=fmt):
                data = export_assembly_to_format(assembly, fmt)
                self.assertIsInstance(data, bytes)
                self.assertGreater(len(data), 0)

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_get_supported_formats(self):
        """Test that supported formats function works."""
        formats = get_supported_formats()
        self.assertIsInstance(formats, list)
        self.assertIn('stl', formats)
        self.assertIn('step', formats)
        # 3MF may or may not be present depending on CadQuery version

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_unsupported_format_error(self):
        """Test that unsupported formats raise appropriate errors."""
        box = cq.Workplane("XY").box(10, 10, 10)

        # Test unsupported format
        with self.assertRaises(ValueError) as context:
            export_shape_to_format(box, 'unsupported_format')

        self.assertIn('Unsupported format', str(context.exception))
        self.assertIn('Available formats', str(context.exception))
