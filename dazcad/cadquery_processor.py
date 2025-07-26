"""CadQuery processing functions for DazCAD."""

import traceback
import unittest

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

# Import core utilities with fallback for direct execution
try:
    from .cadquery_core import color_to_hex, get_location_matrix
    from .export_utils import export_shape_to_stl
except ImportError:
    from cadquery_core import color_to_hex, get_location_matrix
    from export_utils import export_shape_to_stl


def process_regular_object(shown):
    """Process a regular CadQuery object (not an assembly).

    Args:
        shown: Dictionary with 'object', 'name', and 'color' keys

    Returns:
        Dictionary with 'name', 'color', 'stl', and 'transform' keys
    """
    try:
        # Export the shape to STL
        stl_data = export_shape_to_stl(shown['object'])

        # Use provided color or default gray
        color = shown.get('color', '#808080')

        return {
            'name': shown['name'],
            'color': color,
            'stl': stl_data,
            'transform': None  # Regular objects don't have transforms
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error processing regular object {shown['name']}: {e}")
        traceback.print_exc()
        return None


def process_assembly(shown):
    """Process an Assembly object and return list of result objects."""
    results = []
    obj = shown['object']

    print(f"Processing assembly with {len(obj.children)} children")

    for i, child in enumerate(obj.children):
        print(f"\\nProcessing child {i}: {child.name}")

        # Debug: Let's see what's actually in the child object
        print(f"  Child attributes: {dir(child)}")
        if hasattr(child, 'loc'):
            print(f"  Child.loc exists: {child.loc}")
            print(f"  Child.loc type: {type(child.loc)}")
            if child.loc:
                print(f"  Location wrapped: {child.loc.wrapped}")
                trsf = child.loc.wrapped.Transformation()
                print("  Raw transformation values:")
                print(f"    Translation: ({trsf.Value(1,4)}, {trsf.Value(2,4)}, {trsf.Value(3,4)})")

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
                else:
                    print(f"  No location found for {child.name}")

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


def process_objects(shown_objects):
    """Process a list of shown objects and return a flat list of results.

    Args:
        shown_objects: List of dictionaries with 'object', 'name', and 'color' keys

    Returns:
        List of processed object dictionaries ready for visualization
    """
    result_objects = []

    for shown in shown_objects:
        try:
            obj = shown['object']

            # Check if it's an Assembly
            if hasattr(obj, 'children') and hasattr(obj, 'add'):
                # It's an Assembly - process all children
                assembly_results = process_assembly(shown)
                result_objects.extend(assembly_results)
            else:
                # It's a regular CadQuery object
                result = process_regular_object(shown)
                if result:
                    result_objects.append(result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error processing object {shown.get('name', 'Unknown')}: {e}")
            traceback.print_exc()

    return result_objects


class TestCadQueryProcessor(unittest.TestCase):
    """Unit tests for CadQuery processor functions."""

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_process_objects(self):
        """Test the main process_objects function."""
        # Create a simple object
        box = cq.Workplane("XY").box(5, 5, 5)
        shown_objects = [{
            'object': box,
            'name': 'TestBox',
            'color': '#ff0000'
        }]

        # Process the objects
        results = process_objects(shown_objects)

        # Should get one result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'TestBox')
        self.assertEqual(results[0]['color'], '#ff0000')
        self.assertIn('stl', results[0])

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_process_assembly(self):
        """Test processing assemblies."""
        # Create a simple assembly
        assembly = cq.Assembly()
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 5)

        # Add them to assembly with colors
        assembly.add(box1, name="RedBox", color=cq.Color("red"))
        assembly.add(box2, name="GreenBox", color=cq.Color("green"))

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
        self.assertEqual(results[0]['name'], 'TestAssembly_RedBox')
        self.assertEqual(results[1]['name'], 'TestAssembly_GreenBox')

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_process_regular_object(self):
        """Test processing regular objects."""
        # Create a box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Create shown object
        shown = {
            'object': box,
            'name': 'TestBox',
            'color': '#FF0000'
        }

        # Process it
        result = process_regular_object(shown)

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'TestBox')
        self.assertEqual(result['color'], '#FF0000')
        self.assertIn('stl', result)
