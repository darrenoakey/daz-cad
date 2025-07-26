"""CadQuery processing utilities for DazCAD."""

import base64
import os
import tempfile
import traceback
import unittest

import cadquery as cq


def color_to_hex(color_tuple):
    """Convert Color tuple to hex string."""
    if color_tuple:
        # Color tuple is (r, g, b, a) with values 0-1
        # Use round() for more accurate conversion
        r = round(color_tuple[0] * 255)
        g = round(color_tuple[1] * 255)
        b = round(color_tuple[2] * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#808080"


def export_shape_to_stl(shape):
    """Export a shape to STL and return base64 encoded data."""
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Export to STL
        cq.exporters.export(shape, tmp_path, exportType='STL')

        # Read STL file and encode to base64
        with open(tmp_path, 'rb') as f:
            stl_data = base64.b64encode(f.read()).decode('utf-8')
        return stl_data

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def get_location_matrix(location):
    """Convert CadQuery Location to a transformation matrix for Three.js."""
    if not location:
        return None

    # Get the transformation matrix from the location
    trsf = location.wrapped.Transformation()

    # Extract the 3x3 rotation matrix and translation from OCC
    # CadQuery uses: X=right, Y=forward/back, Z=up
    # Three.js uses: X=right, Y=up, Z=forward/back
    # So we need to swap Y and Z coordinates

    matrix = []

    # First row (X axis) - keep X, swap Y↔Z
    matrix.extend([
        trsf.Value(1, 1),  # XX stays
        trsf.Value(1, 3),  # XZ → XY
        trsf.Value(1, 2),  # XY → XZ
        0
    ])

    # Second row (Y axis) - this becomes Z in Three.js, so use CadQuery's Z row
    matrix.extend([
        trsf.Value(3, 1),  # ZX → YX
        trsf.Value(3, 3),  # ZZ → YY
        trsf.Value(3, 2),  # ZY → YZ
        0
    ])

    # Third row (Z axis) - this becomes Y in Three.js, so use CadQuery's Y row
    matrix.extend([
        trsf.Value(2, 1),  # YX → ZX
        trsf.Value(2, 3),  # YZ → ZY
        trsf.Value(2, 2),  # YY → ZZ
        0
    ])

    # Translation - swap Y and Z coordinates
    trans = trsf.TranslationPart()
    matrix.extend([
        trans.X(),  # X stays the same
        trans.Z(),  # Z becomes Y (up)
        trans.Y(),  # Y becomes Z (forward/back)
        1
    ])

    return matrix


def process_assembly(shown):
    """Process an Assembly object and return list of result objects."""
    results = []
    obj = shown['object']

    print(f"Processing assembly with {len(obj.children)} children")

    for i, child in enumerate(obj.children):
        print(f"\\nProcessing child {i}: {child.name}")

        # Assembly children have an 'obj' attribute containing the shape
        if hasattr(child, 'obj'):
            shape = child.obj

            try:
                # Export the shape at origin (untransformed)
                stl_data = export_shape_to_stl(shape)

                color_tuple = child.color.toTuple() if child.color else None
                part_color = color_to_hex(color_tuple)

                # Get transformation matrix if location exists
                transform = None
                if hasattr(child, 'loc') and child.loc:
                    transform = get_location_matrix(child.loc)
                    print(f"  Transform matrix: {transform}")

                results.append({
                    'name': f"{shown['name']}_{child.name}",
                    'color': part_color,
                    'stl': stl_data,
                    'transform': transform  # Include transformation matrix
                })
                print(f"  Successfully exported {child.name} with color {part_color}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"  Error exporting {child.name}: {e}")
                traceback.print_exc()

    return results


def process_regular_object(shown):
    """Process a regular CadQuery object and return result object."""
    obj = shown['object']

    # Skip if not a CadQuery object
    if not hasattr(obj, 'val') and not hasattr(obj, 'exportStl'):
        return None

    # Create temporary STL file
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Export to STL using CadQuery's built-in exporter
        if hasattr(obj, 'exportStl'):
            obj.exportStl(tmp_path)
        else:
            # For other CadQuery objects, try to export
            cq.exporters.export(obj, tmp_path, exportType='STL')

        # Read STL file and encode to base64
        with open(tmp_path, 'rb') as f:
            stl_data = base64.b64encode(f.read()).decode('utf-8')

        return {
            'name': shown['name'],
            'color': shown['color'] or '#808080',
            'stl': stl_data,
            'transform': None  # No transform for regular objects
        }

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def process_objects(shown_objs):
    """Process all shown objects and return results."""
    result_objects = []

    for shown in shown_objs:
        obj = shown['object']
        print(f"\\nProcessing shown object: {shown['name']}")
        print(f"Object type: {type(obj)}")

        # Check if it's an Assembly
        is_assembly = isinstance(obj, cq.Assembly)
        print(f"Is assembly: {is_assembly}")

        if is_assembly:
            # Process assembly parts
            results = process_assembly(shown)
            result_objects.extend(results)
        else:
            # Process regular object
            result = process_regular_object(shown)
            if result:
                result_objects.append(result)

    return result_objects


class CadQueryProcessorTests(unittest.TestCase):
    """Test CadQuery processing functionality"""

    def test_color_to_hex(self):
        """Test color conversion"""
        self.assertEqual(color_to_hex((1.0, 0.0, 0.0)), "#ff0000")
        self.assertEqual(color_to_hex((0.0, 1.0, 0.0)), "#00ff00")
        self.assertEqual(color_to_hex((0.0, 0.0, 1.0)), "#0000ff")

    def test_export_shape_to_stl(self):
        """Test STL export"""
        box = cq.Workplane("XY").box(1, 1, 1)
        stl_data = export_shape_to_stl(box)
        self.assertIsNotNone(stl_data)
        self.assertIsInstance(stl_data, str)

    def test_process_regular_object(self):
        """Test processing a regular CadQuery object"""
        box = cq.Workplane("XY").box(1, 1, 1)
        shown = {'object': box, 'name': 'TestBox', 'color': '#ff0000'}
        result = process_regular_object(shown)
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'TestBox')
        self.assertEqual(result['color'], '#ff0000')

    def test_coordinate_transformation(self):
        """Test that coordinates are properly transformed from CadQuery to Three.js"""
        # Create a simple location with translation only
        # In CadQuery: move 1 unit right (X), 2 units forward (Y), 3 units up (Z)
        location = cq.Location((1, 2, 3), (0, 0, 0))  # translation, rotation
        matrix = get_location_matrix(location)

        # In the resulting Three.js matrix, we expect:
        # X=1 (unchanged), Y=3 (was Z), Z=2 (was Y)
        # Matrix is in column-major format: [m00,m10,m20,m30, m01,m11,m21,m31, ...]
        # Translation is in positions 12, 13, 14
        self.assertIsNotNone(matrix)
        self.assertEqual(len(matrix), 16)
        self.assertEqual(matrix[12], 1)  # X translation unchanged
        self.assertEqual(matrix[13], 3)  # Y translation = CadQuery Z
        self.assertEqual(matrix[14], 2)  # Z translation = CadQuery Y
