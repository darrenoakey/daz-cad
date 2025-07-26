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
    """Convert CadQuery Location to transformation matrix - no coordinate conversion."""
    if not location:
        return None

    # Get the transformation matrix from the location
    trsf = location.wrapped.Transformation()

    # Extract the raw transformation matrix without any coordinate system conversion
    # Since we fixed the coordinate system in Three.js with Z-up, we can use the 
    # CadQuery transformation matrix directly
    matrix = [
        trsf.Value(1, 1), trsf.Value(1, 2), trsf.Value(1, 3), 0,  # Row 1
        trsf.Value(2, 1), trsf.Value(2, 2), trsf.Value(2, 3), 0,  # Row 2  
        trsf.Value(3, 1), trsf.Value(3, 2), trsf.Value(3, 3), 0,  # Row 3
        trsf.Value(1, 4), trsf.Value(2, 4), trsf.Value(3, 4), 1   # Translation + homogeneous
    ]

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
