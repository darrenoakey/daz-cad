"""Core CadQuery utility functions for DazCAD."""

import base64
import os
import tempfile
import unittest

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False


def color_to_hex(color_tuple):
    """Convert an RGBA color tuple to hex string.

    Args:
        color_tuple: A tuple of (r, g, b, a) values from 0.0 to 1.0, or None

    Returns:
        Hex color string like '#ff0000'
    """
    if color_tuple is None:
        return "#808080"  # Default gray

    # Convert from 0.0-1.0 range to 0-255 range
    r = int(round(color_tuple[0] * 255))
    g = int(round(color_tuple[1] * 255))
    b = int(round(color_tuple[2] * 255))

    # Clamp values to 0-255 range
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))

    return f"#{r:02x}{g:02x}{b:02x}"


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


def get_location_matrix(location):
    """Convert a CadQuery Location to a 4x4 transformation matrix.

    Args:
        location: A CadQuery Location object

    Returns:
        A list of 16 numbers representing a 4x4 transformation matrix
        in row-major order for Three.js
    """
    if not location or not hasattr(location, 'wrapped'):
        return None

    try:
        # Get the underlying OpenCascade transformation
        trsf = location.wrapped.Transformation()

        # Extract the 4x4 matrix values
        # OpenCascade uses 1-based indexing for matrix access
        matrix = [
            # Row 1
            trsf.Value(1, 1), trsf.Value(1, 2), trsf.Value(1, 3), trsf.Value(1, 4),
            # Row 2
            trsf.Value(2, 1), trsf.Value(2, 2), trsf.Value(2, 3), trsf.Value(2, 4),
            # Row 3
            trsf.Value(3, 1), trsf.Value(3, 2), trsf.Value(3, 3), trsf.Value(3, 4),
            # Row 4 (always 0, 0, 0, 1 for affine transformations)
            0.0, 0.0, 0.0, 1.0
        ]

        return matrix

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error extracting transformation matrix: {e}")
        return None


class TestCadQueryCore(unittest.TestCase):
    """Unit tests for CadQuery core utility functions."""

    def test_color_to_hex_basic_colors(self):
        """Test basic color conversions."""
        # Test red
        self.assertEqual(color_to_hex((1.0, 0.0, 0.0, 1.0)), "#ff0000")
        # Test green
        self.assertEqual(color_to_hex((0.0, 1.0, 0.0, 1.0)), "#00ff00")
        # Test blue
        self.assertEqual(color_to_hex((0.0, 0.0, 1.0, 1.0)), "#0000ff")

    def test_color_to_hex_mixed_colors(self):
        """Test mixed color conversions."""
        # Test gray (0.5 * 255 = 127.5, rounds to 128 = 0x80)
        self.assertEqual(color_to_hex((0.5, 0.5, 0.5, 1.0)), "#808080")
        # Test None (defaults to gray)
        self.assertEqual(color_to_hex(None), "#808080")

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
    def test_get_location_matrix(self):
        """Test location matrix extraction."""
        # Test with None
        self.assertIsNone(get_location_matrix(None))

        # Test with translation - use same pattern as README example
        # pylint: disable=no-value-for-parameter
        translation_loc = cq.Location((10, 20, 30))
        # pylint: enable=no-value-for-parameter
        matrix = get_location_matrix(translation_loc)
        self.assertIsNotNone(matrix)
        self.assertEqual(len(matrix), 16)
        # Check translation values (positions 3, 7, 11 in row-major 4x4)
        self.assertEqual(matrix[3], 10.0)  # X translation
        self.assertEqual(matrix[7], 20.0)  # Y translation
        self.assertEqual(matrix[11], 30.0)  # Z translation
