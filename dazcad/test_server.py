"""Unit tests for the DazCAD server."""

import unittest
from unittest.mock import MagicMock

# Try to import server module - handle case where dependencies aren't available
try:
    from . import server
    IMPORTS_AVAILABLE = True
except ImportError:
    try:
        import server  # Direct import for when running tests standalone
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
