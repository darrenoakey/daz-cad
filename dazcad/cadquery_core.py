"""Core CadQuery utility functions for DazCAD."""

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
