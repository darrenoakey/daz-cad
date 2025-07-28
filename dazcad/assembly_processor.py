"""Assembly processing utilities for DazCAD."""

import traceback
import unittest

# Import dependencies with fallback for direct execution
try:
    from .cadquery_core import get_location_matrix
    from .export_utils import export_shape_to_stl
    from .color_processor import process_child_color
except ImportError:
    from cadquery_core import get_location_matrix
    from export_utils import export_shape_to_stl
    from color_processor import process_child_color

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False


def process_assembly_child(child, assembly_name):
    """Process a single assembly child and return result object.

    Args:
        child: Assembly child object
        assembly_name: Name of the parent assembly

    Returns:
        Dictionary with processed child data or None if error
    """
    print(f"  Child attributes: {dir(child)}")

    # Debug location information
    if hasattr(child, 'loc'):
        print(f"  Child.loc exists: {child.loc}")
        print(f"  Child.loc type: {type(child.loc)}")
        if child.loc:
            print(f"  Location wrapped: {child.loc.wrapped}")
            trsf = child.loc.wrapped.Transformation()
            print("  Raw transformation values:")
            translation_values = (trsf.Value(1,4), trsf.Value(2,4), trsf.Value(3,4))
            print(f"    Translation: {translation_values}")

    # Assembly children have an 'obj' attribute containing the shape
    if not hasattr(child, 'obj'):
        print(f"  Child {child.name} has no 'obj' attribute")
        return None

    shape = child.obj

    try:
        # Export the shape at origin (untransformed)
        stl_data = export_shape_to_stl(shape)

        # Process the color
        part_color = process_child_color(child.color)

        # Get transformation matrix if location exists
        transform = None
        if hasattr(child, 'loc') and child.loc:
            transform = get_location_matrix(child.loc)
            print(f"  Transform matrix: {transform}")
        else:
            print(f"  No location found for {child.name}")

        result = {
            'name': f"{assembly_name}_{child.name}",
            'color': part_color,
            'stl': stl_data,
            'transform': transform  # Include transformation matrix
        }
        print(f"  Successfully exported {child.name} with color {part_color}")
        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"  Error exporting {child.name}: {e}")
        traceback.print_exc()
        return None


def process_assembly(shown):
    """Process an Assembly object and return list of result objects."""
    results = []
    obj = shown['object']

    print(f"Processing assembly with {len(obj.children)} children")

    for i, child in enumerate(obj.children):
        print(f"\\nProcessing child {i}: {child.name}")

        result = process_assembly_child(child, shown['name'])
        if result:
            results.append(result)

    return results


class TestAssemblyProcessor(unittest.TestCase):
    """Tests for assembly processing utilities."""

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_process_assembly(self):
        """Test processing assemblies."""
        # Create a simple assembly
        assembly = cq.Assembly()
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 5)

        # Add them to assembly with colors
        assembly.add(box1, name="TestBox1", color=cq.Color("red"))
        assembly.add(box2, name="TestBox2", color=cq.Color("green"))

        # Create shown object
        shown = {
            'object': assembly,
            'name': 'TestAssembly',
            'color': None
        }

        # Process the assembly
        results = process_assembly(shown)

        # Should get two results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['name'], 'TestAssembly_TestBox1')
        self.assertEqual(results[1]['name'], 'TestAssembly_TestBox2')

    def test_process_assembly_child_no_obj(self):
        """Test processing child without obj attribute."""
        # Mock child without obj attribute
        class MockChild:  # pylint: disable=too-few-public-methods
            """Mock child for testing."""
            def __init__(self):
                self.name = "TestChild"

        child = MockChild()
        result = process_assembly_child(child, "TestAssembly")
        self.assertIsNone(result)
