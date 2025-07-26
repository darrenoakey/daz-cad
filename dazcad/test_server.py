"""Unit tests for the DazCAD server."""

import base64
import unittest
from unittest.mock import MagicMock

# Try to import server module - handle case where dependencies aren't available
try:
    from . import server
    from . import cadquery_processor
except ImportError:
    import server
    import cadquery_processor

try:
    import cadquery as cq
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@unittest.skipIf(not IMPORTS_AVAILABLE, "Server module not available")
class TestServer(unittest.TestCase):
    """Tests for the DazCAD server."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear shown_objects
        server.shown_objects.clear()

    def test_show_object(self):
        """Test the show_object function."""
        mock_obj = MagicMock()
        result = server.show_object(mock_obj, "TestObject", "#FF0000")

        self.assertEqual(result, mock_obj)
        self.assertEqual(len(server.shown_objects), 1)
        self.assertEqual(server.shown_objects[0]['name'], "TestObject")
        self.assertEqual(server.shown_objects[0]['color'], "#FF0000")

    def test_show_object_defaults(self):
        """Test show_object with default values."""
        mock_obj = MagicMock()
        server.show_object(mock_obj)

        self.assertEqual(server.shown_objects[0]['name'], 'Object_0')
        self.assertIsNone(server.shown_objects[0]['color'])

    def test_show_object_multiple(self):
        """Test multiple show_object calls."""
        obj1 = MagicMock()
        obj2 = MagicMock()
        obj3 = MagicMock()

        server.show_object(obj1)
        server.show_object(obj2, "SecondObject")
        server.show_object(obj3, color="#00FF00")

        self.assertEqual(len(server.shown_objects), 3)
        self.assertEqual(server.shown_objects[0]['name'], 'Object_0')
        self.assertEqual(server.shown_objects[1]['name'], 'SecondObject')
        self.assertEqual(server.shown_objects[2]['name'], 'Object_2')
        self.assertEqual(server.shown_objects[2]['color'], '#00FF00')

    def test_color_to_hex(self):
        """Test color tuple to hex conversion."""
        # Test red
        self.assertEqual(cadquery_processor.color_to_hex((1.0, 0.0, 0.0, 1.0)), "#ff0000")
        # Test blue
        self.assertEqual(cadquery_processor.color_to_hex((0.0, 0.0, 1.0, 1.0)), "#0000ff")
        # Test green
        self.assertEqual(cadquery_processor.color_to_hex((0.0, 1.0, 0.0, 1.0)), "#00ff00")
        # Test mixed color (0.5 * 255 = 127.5, rounds to 128 = 0x80)
        self.assertEqual(cadquery_processor.color_to_hex((0.5, 0.5, 0.5, 1.0)), "#808080")
        # Test None
        self.assertEqual(cadquery_processor.color_to_hex(None), "#808080")

    @unittest.skipIf(not IMPORTS_AVAILABLE, "CadQuery not available")
    def test_simple_assembly(self):
        """Test a simple assembly without location transforms."""
        # Create a simple assembly
        assembly = cq.Assembly()

        # Create two boxes at origin
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 5)

        # Add them to assembly with colors, no location
        assembly.add(box1, name="RedBox", color=cq.Color("red"))
        assembly.add(box2, name="GreenBox", color=cq.Color("green"))

        # Create shown object
        shown = {
            'object': assembly,
            'name': 'SimpleAssembly',
            'color': None
        }

        # Process the assembly
        results = cadquery_processor.process_assembly(shown)

        # Verify results
        self.assertEqual(len(results), 2)

        # Check first box
        self.assertEqual(results[0]['name'], 'SimpleAssembly_RedBox')
        self.assertEqual(results[0]['color'], '#ff0000')

        # Check second box
        self.assertEqual(results[1]['name'], 'SimpleAssembly_GreenBox')
        self.assertEqual(results[1]['color'], '#00ff00')

    @unittest.skipIf(not IMPORTS_AVAILABLE, "CadQuery not available")
    def test_export_shape_to_stl(self):
        """Test exporting a shape to STL."""
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Export it
        stl_data = cadquery_processor.export_shape_to_stl(box)

        # Verify it's valid base64
        # pylint: disable=broad-exception-caught
        try:
            decoded = base64.b64decode(stl_data)
            self.assertGreater(len(decoded), 0)
        except Exception:
            self.fail("STL data is not valid base64")
        # pylint: enable=broad-exception-caught

    @unittest.skipIf(not IMPORTS_AVAILABLE, "CadQuery not available")
    def test_process_regular_object(self):
        """Test processing a regular CadQuery object."""
        # Create a box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Create shown object
        shown = {
            'object': box,
            'name': 'TestBox',
            'color': '#FF0000'
        }

        # Process it
        result = cadquery_processor.process_regular_object(shown)

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'TestBox')
        self.assertEqual(result['color'], '#FF0000')
        self.assertIn('stl', result)
