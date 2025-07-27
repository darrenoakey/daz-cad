"""Core server functionality for DazCAD."""

import sys
import unittest
from io import StringIO

import cadquery as cq

# Import dependencies with fallback for direct execution
try:
    from .cadquery_processor import process_objects
    from .library_manager import LibraryManager
except ImportError:
    # Fallback for direct execution
    from cadquery_processor import process_objects
    from library_manager import LibraryManager

# Store for objects shown via show_object
shown_objects = []

# Initialize library manager
library_manager = LibraryManager()


def show_object(obj, name=None, color=None):
    """Capture objects to be displayed."""
    shown_objects.append({
        'object': obj,
        'name': name or f'Object_{len(shown_objects)}',
        'color': color
    })
    return obj


def run_cadquery_code(code_str):
    """Execute CadQuery code and capture results"""
    global shown_objects  # pylint: disable=global-statement
    shown_objects = []

    # Import everything needed for exec environment
    # pylint: disable=import-outside-toplevel
    from cadquery import Color, Assembly, Location, Workplane, Vector
    import traceback
    # pylint: enable=import-outside-toplevel

    # Prepare execution environment
    exec_globals = {
        'cq': cq,
        'Color': Color,
        'Assembly': Assembly,
        'Location': Location,
        'Workplane': Workplane,
        'Vector': Vector,
        'show_object': show_object,
        '__name__': '__main__'
    }

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # pylint: disable=exec-used
        exec(code_str, exec_globals)
        # pylint: enable=exec-used
        output = sys.stdout.getvalue()
    except Exception as e:  # pylint: disable=broad-exception-caught
        output = None
        # Get full traceback with line numbers
        error_traceback = traceback.format_exc()
        return {"success": False, "error": str(e), "traceback": error_traceback, "objects": []}
    finally:
        sys.stdout = old_stdout

    # Process shown objects
    result_objects = process_objects(shown_objects)

    return {"success": True, "objects": result_objects, "output": output}


class TestServerCore(unittest.TestCase):
    """Tests for server core functionality."""

    def test_show_object(self):
        """Test the show_object function."""
        global shown_objects  # pylint: disable=global-statement
        shown_objects = []

        # Create a test object
        test_box = cq.Workplane("XY").box(10, 10, 10)
        result = show_object(test_box, name="TestBox", color="red")

        # Check that object was captured
        self.assertEqual(len(shown_objects), 1)
        self.assertEqual(shown_objects[0]['name'], "TestBox")
        self.assertEqual(shown_objects[0]['color'], "red")
        self.assertEqual(result, test_box)

    def test_run_cadquery_code(self):
        """Test running CadQuery code."""
        code = '''
import cadquery as cq
box = cq.Workplane("XY").box(10, 10, 10)
show_object(box, name="test_box")
'''
        result = run_cadquery_code(code)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["objects"]), 1)
        self.assertIn("test_box", [obj["name"] for obj in result["objects"]])

    def test_library_manager_initialized(self):
        """Test that library manager is properly initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))
        self.assertTrue(hasattr(library_manager, 'get_file_content'))
        self.assertTrue(hasattr(library_manager, 'save_file'))
