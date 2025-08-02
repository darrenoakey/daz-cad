"""Shape export utilities for CadQuery objects."""

import base64
import os
import tempfile
import unittest


def export_shape_to_stl(shape, name: str = "export") -> str:
    """Export a CadQuery shape to STL format.

    Args:
        shape: CadQuery shape to export (Workplane or Shape)
        name: Name for the export

    Returns:
        STL content as base64-encoded string

    Raises:
        AttributeError: If the shape doesn't have required methods
        ValueError: If the export returns empty content
        IOError: If temporary file operations fail
    """
    try:
        import cadquery as cq  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError as e:
        error_msg = f"CadQuery is required for STL export of {name}"
        print(f"ERROR: {error_msg}")
        raise ImportError(error_msg) from e

    # Handle CadQuery Workplane objects
    if hasattr(shape, 'val'):
        # Extract the shape from Workplane
        actual_shape = shape.val()
    else:
        actual_shape = shape

    # Export using the proper method
    try:
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        # Use the standard cq.exporters.export method
        cq.exporters.export(actual_shape, tmp_filename, exportType="STL")

        with open(tmp_filename, 'rb') as f:
            stl_content = f.read()

        os.unlink(tmp_filename)

    except Exception as e:
        error_msg = f"Failed to export shape {name} to STL: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise AttributeError(error_msg) from e

    # Ensure we have content
    if not stl_content:
        error_msg = f"STL export for {name} returned empty content"
        print(f"ERROR: {error_msg}")
        raise ValueError(error_msg)

    # Validate minimum size for actual STL content
    if len(stl_content) < 84:  # Minimum for binary STL header
        raise ValueError(f"STL export for {name} returned insufficient data: "
                        f"{len(stl_content)} bytes")

    # Base64 encode and return
    encoded = base64.b64encode(stl_content).decode('utf-8')
    print(f"Successfully exported {name}: {len(encoded)} characters (base64)")
    return encoded


def export_shape_to_format(shape, format_name: str) -> bytes:
    """Export a CadQuery shape to specified format.

    Args:
        shape: CadQuery shape to export
        format_name: Target format (stl, step, 3mf)

    Returns:
        Exported data as bytes

    Raises:
        AttributeError: If the shape doesn't have required methods
        ValueError: If the format is not supported or export fails
        ImportError: If CadQuery is not available
    """
    try:
        import cadquery as cq  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError as e:
        raise ImportError("CadQuery is required for export operations") from e

    format_lower = format_name.lower()

    # Handle CadQuery Workplane objects
    if hasattr(shape, 'val'):
        # Extract the shape from Workplane
        actual_shape = shape.val()
    else:
        actual_shape = shape

    # Export based on format using cq.exporters.export
    with tempfile.NamedTemporaryFile(suffix=f'.{format_lower}', delete=False) as tmp_file:
        tmp_filename = tmp_file.name

    try:
        if format_lower == "stl":
            cq.exporters.export(actual_shape, tmp_filename, exportType="STL")
        elif format_lower == "step":
            cq.exporters.export(actual_shape, tmp_filename, exportType="STEP")
        elif format_lower == "3mf":
            # 3MF support may vary by CadQuery version
            try:
                cq.exporters.export(actual_shape, tmp_filename, exportType="3MF")
            except Exception as e:
                os.unlink(tmp_filename)
                raise ValueError(f"3MF export not supported in this CadQuery version: {e}") from e
        else:
            os.unlink(tmp_filename)
            raise ValueError(f"Export format '{format_name}' is not supported")

        # Read the exported file
        with open(tmp_filename, 'rb') as f:
            result = f.read()

        # Clean up temporary file
        os.unlink(tmp_filename)

    except Exception as e:
        # Clean up temporary file on error
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
        raise e

    # Validate result has meaningful content
    if len(result) < 10:  # Minimum meaningful content
        raise ValueError(f"Export to {format_name} returned insufficient data: "
                        f"{len(result)} bytes")

    return result


class TestShapeExports(unittest.TestCase):
    """Tests for shape export utilities."""

    def test_export_shape_to_stl_with_invalid_input(self):
        """Test STL export functionality with invalid input."""
        # Test with None should raise AttributeError
        with self.assertRaises(AttributeError):
            export_shape_to_stl(None, "test")

    def test_export_shape_to_format_with_invalid_input(self):
        """Test exporting shape to format with invalid input."""
        # Test with None should raise TypeError (from CadQuery internals)
        with self.assertRaises((AttributeError, TypeError)):
            export_shape_to_format(None, "stl")

    def test_export_shape_to_format_unsupported_format(self):
        """Test exporting shape to unsupported format."""
        # Mock shape with toSTL method
        mock_shape = type('MockShape', (), {'toSTL': lambda: 'mock data'})()

        # Test unsupported format should raise ValueError
        with self.assertRaises(ValueError) as context:
            export_shape_to_format(mock_shape, "unsupported")

        self.assertIn("not supported", str(context.exception))
