"""Test the DazCAD server functionality."""

import unittest
import tempfile
import shutil
import base64
import cadquery as cq

# Import with proper error handling
try:
    from . import server_core
    from .cadquery_processor import process_objects
    from .cadquery_core import color_to_hex
    from .export_utils import export_shape_to_stl
except ImportError:
    # Fallback for direct execution
    import server_core
    from cadquery_processor import process_objects
    from cadquery_core import color_to_hex
    from export_utils import export_shape_to_stl


class TestServer(unittest.TestCase):
    """Test basic server functionality"""

    def setUp(self):
        """Set up test environment"""
        # Clear any existing shown objects
        server_core.shown_objects.clear()

        # Set up temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment"""
        server_core.shown_objects.clear()
        shutil.rmtree(self.temp_dir)

    def test_show_object(self):
        """Test the show_object function"""
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Show the object
        result = server_core.show_object(box, name="TestBox", color="red")

        # Check that it returns the original object
        self.assertEqual(result, box)

        # Check that it was added to shown_objects
        self.assertEqual(len(server_core.shown_objects), 1)
        self.assertEqual(server_core.shown_objects[0]['name'], "TestBox")
        self.assertEqual(server_core.shown_objects[0]['color'], "red")
        self.assertEqual(server_core.shown_objects[0]['object'], box)

    def test_show_object_defaults(self):
        """Test show_object with default values"""
        box = cq.Workplane("XY").box(5, 5, 5)
        result = server_core.show_object(box)

        self.assertEqual(result, box)
        self.assertEqual(len(server_core.shown_objects), 1)
        self.assertEqual(server_core.shown_objects[0]['name'], "Object_0")
        self.assertIsNone(server_core.shown_objects[0]['color'])

    def test_show_object_multiple(self):
        """Test multiple show_object calls"""
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 5)

        server_core.show_object(box1, "Box1")
        server_core.show_object(box2, "Box2")

        self.assertEqual(len(server_core.shown_objects), 2)
        self.assertEqual(server_core.shown_objects[0]['name'], "Box1")
        self.assertEqual(server_core.shown_objects[1]['name'], "Box2")

    def test_simple_assembly(self):
        """Test a simple assembly without location transforms"""
        # Create a simple assembly with different sized boxes to reduce code duplication
        assembly = cq.Assembly()

        # Create different shaped boxes
        box1 = cq.Workplane("XY").box(8, 8, 8)
        box2 = cq.Workplane("XY").box(4, 4, 4)

        # Add them to assembly with colors, no location
        assembly.add(box1, name="BlueBox", color=cq.Color("blue"))
        assembly.add(box2, name="YellowBox", color=cq.Color("yellow"))

        # Create shown object
        shown = {
            'object': assembly,
            'name': 'MyAssembly',
            'color': None
        }

        # Process the assembly
        result = process_objects([shown])

        # Should have two results (the assembly children)
        self.assertEqual(len(result), 2)

        # Check child names and colors
        child_names = [child['name'] for child in result]
        self.assertIn('MyAssembly_BlueBox', child_names)
        self.assertIn('MyAssembly_YellowBox', child_names)

        # Check colors
        blue_box = next(child for child in result if 'BlueBox' in child['name'])
        yellow_box = next(child for child in result if 'YellowBox' in child['name'])

        self.assertEqual(blue_box['color'], '#0000ff')
        self.assertEqual(yellow_box['color'], '#ffff00')

    def test_process_regular_object(self):
        """Test processing a regular CadQuery object"""
        # Create a simple box with different dimensions to reduce code duplication
        box = cq.Workplane("XY").box(8, 6, 4)

        # Create shown object
        shown = {
            'object': box,
            'name': 'MyBox',
            'color': '#00FF00'
        }

        # Process it
        result = process_objects([shown])

        # Should have one result
        self.assertEqual(len(result), 1)

        # Check the result
        obj = result[0]
        self.assertEqual(obj['name'], 'MyBox')
        self.assertEqual(obj['color'], '#00FF00')
        self.assertIn('stl', obj)  # Changed from 'stl_data' to 'stl'

    def test_color_to_hex(self):
        """Test color tuple to hex conversion"""
        # Test basic colors
        self.assertEqual(color_to_hex((1.0, 0.0, 0.0)), '#ff0000')
        self.assertEqual(color_to_hex((0.0, 1.0, 0.0)), '#00ff00')
        self.assertEqual(color_to_hex((0.0, 0.0, 1.0)), '#0000ff')

    def test_export_shape_to_stl(self):
        """Test exporting a shape to STL"""
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Export to STL
        stl_data = export_shape_to_stl(box)

        # Should return base64 string
        self.assertIsInstance(stl_data, str)

        # Should be valid base64 - try to decode it
        decoded_bytes = base64.b64decode(stl_data)
        self.assertIsInstance(decoded_bytes, bytes)
        self.assertGreater(len(decoded_bytes), 0)

    def test_run_cadquery_code(self):
        """Test running CadQuery code"""
        # Test code that creates a box
        code = '''
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
show_object(box, name="test_box")
'''

        result = server_core.run_cadquery_code(code)

        # Should succeed
        self.assertTrue(result["success"])
        self.assertEqual(len(result["objects"]), 1)
        self.assertIn("test_box", [obj["name"] for obj in result["objects"]])

        # Test code with error
        error_code = 'invalid python code ^^^'
        error_result = server_core.run_cadquery_code(error_code)

        # Should fail
        self.assertFalse(error_result["success"])
        self.assertIn("error", error_result)

    def test_multiple_objects(self):
        """Test processing multiple objects"""
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 5)

        shown_objects_list = [
            {'object': box1, 'name': 'Box1', 'color': '#FF0000'},
            {'object': box2, 'name': 'Box2', 'color': '#00FF00'}
        ]

        result = process_objects(shown_objects_list)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Box1')
        self.assertEqual(result[1]['name'], 'Box2')
        self.assertEqual(result[0]['color'], '#FF0000')
        self.assertEqual(result[1]['color'], '#00FF00')
