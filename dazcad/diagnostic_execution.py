"""Library file execution diagnostic functions."""

import base64
import os
import sys
import traceback
import unittest
from io import StringIO

# Import dependencies
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .library_manager import LibraryManager
except ImportError:
    try:
        from library_manager import LibraryManager
    except ImportError:
        LibraryManager = None

try:
    from .export_utils import export_shape_to_stl
except ImportError:
    try:
        from export_utils import export_shape_to_stl
    except ImportError:
        export_shape_to_stl = None


def test_library_file_execution():  # pylint: disable=too-many-locals
    """Test executing a library file."""
    if not CADQUERY_AVAILABLE or LibraryManager is None:
        print("✗ Prerequisites not met for library execution test")
        return False

    try:
        # Get library manager
        current_dir = os.path.dirname(os.path.abspath(__file__))
        library_path = os.path.join(current_dir, "library")
        manager = LibraryManager(built_in_library_path=library_path)

        # Get library files
        files = manager.list_files()
        if not files['built_in']:
            print("✗ No library files found")
            return False

        # Try to execute the first library file
        test_file = files['built_in'][0]
        content = manager.get_file_content(test_file)

        print(f"Testing execution of {test_file}")

        # Set up execution environment
        shown_objects = []

        def show_object(obj, name=None, color=None):
            shown_objects.append({
                'object': obj,
                'name': name or f'Object_{len(shown_objects)}',
                'color': color
            })
            return obj

        exec_globals = {
            'cq': cq,
            'cadquery': cq,
            'show_object': show_object,
            'show': show_object,
            '__name__': '__main__'
        }

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # Execute the code
            exec(content, exec_globals)  # pylint: disable=exec-used

            output = sys.stdout.getvalue()
            print("✓ Library file executed successfully")
            print(f"Objects created: {len(shown_objects)}")
            if output:
                print(f"Output: {output[:100]}...")

            # Test exporting one of the objects
            if shown_objects and export_shape_to_stl:
                obj = shown_objects[0]
                stl_data = export_shape_to_stl(obj['object'], obj['name'])

                # Check if it's the minimal STL
                decoded = base64.b64decode(stl_data)
                decoded_str = decoded.decode('utf-8')

                if "solid empty" in decoded_str:
                    print(f"✗ Object {obj['name']} exported as empty STL")
                    return False
                print(f"✓ Object {obj['name']} exported successfully")
                return True

            return len(shown_objects) > 0

        finally:
            sys.stdout = old_stdout

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"✗ Library execution test failed: {e}")
        traceback.print_exc()
        return False


class TestExecutionDiagnostics(unittest.TestCase):
    """Tests for library execution diagnostic functions."""

    def test_library_execution_function(self):
        """Test that test_library_file_execution function exists."""
        self.assertTrue(callable(test_library_file_execution))
