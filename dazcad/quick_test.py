#!/usr/bin/env python3
"""Quick test script to diagnose DazCAD issues."""

import base64
import os
import sys
import tempfile
import traceback
import unittest

# Add the current directory to the path so we can import dazcad modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import modules with fallbacks
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    cq = None
    CADQUERY_AVAILABLE = False

try:
    from library_manager import LibraryManager
    LIBRARY_MANAGER_AVAILABLE = True
except ImportError:
    LibraryManager = None
    LIBRARY_MANAGER_AVAILABLE = False

try:
    from export_utils import export_shape_to_stl
    EXPORT_UTILS_AVAILABLE = True
except ImportError:
    export_shape_to_stl = None
    EXPORT_UTILS_AVAILABLE = False

try:
    from server_core import run_cadquery_code
    SERVER_CORE_AVAILABLE = True
except ImportError:
    run_cadquery_code = None
    SERVER_CORE_AVAILABLE = False


def test_quick_library_loading():
    """Quick test of library loading."""
    print("=== Testing Library Loading ===")

    if not LIBRARY_MANAGER_AVAILABLE:
        print("ERROR: LibraryManager not available")
        return False

    try:
        # Initialize with the correct library path
        library_path = os.path.join(current_dir, "library")
        print(f"Library path: {library_path}")
        print(f"Library path exists: {os.path.exists(library_path)}")

        if os.path.exists(library_path):
            files = os.listdir(library_path)
            print(f"Files in library directory: {files}")

        manager = LibraryManager(built_in_library_path=library_path)
        files = manager.list_files()

        print(f"Library manager found: {files}")

        # Try to read the first file
        if files['built_in']:
            test_file = files['built_in'][0]
            print(f"Testing read of: {test_file}")
            content = manager.get_file_content(test_file)
            print(f"Successfully read {test_file}: {len(content)} characters")
            return True

        print("ERROR: No built-in library files found!")
        return False

    except (OSError, FileNotFoundError, KeyError, AttributeError) as e:
        print(f"ERROR in library loading test: {e}")
        traceback.print_exc()
        return False


def test_quick_cadquery():
    """Quick test of CadQuery functionality."""
    print("\\n=== Testing CadQuery ===")

    if not CADQUERY_AVAILABLE:
        print("ERROR: CadQuery not available")
        return False

    try:
        print("✓ CadQuery imported successfully")

        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)
        print("✓ Box created successfully")

        # Test shape extraction
        shape = box.val()
        print("✓ Shape extracted successfully")

        # Test STL export using the proper export function
        try:
            stl_data = export_shape_to_stl(shape, "test_box")
            print(f"✓ STL export successful: {len(stl_data)} bytes")
        except (ImportError, TypeError):
            # Fallback to direct CadQuery export
            with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
                cq.exporters.export(shape, tmp_file.name, exportType="STL")
                with open(tmp_file.name, 'rb') as f:
                    stl_data = f.read()
                os.unlink(tmp_file.name)
            print(f"✓ STL export successful: {len(stl_data)} bytes")

        return True

    except (AttributeError, TypeError, ValueError) as e:
        print(f"ERROR in CadQuery test: {e}")
        traceback.print_exc()
        return False


def test_quick_export():
    """Quick test of export functionality."""
    print("\\n=== Testing Export ===")

    if not CADQUERY_AVAILABLE:
        print("ERROR: CadQuery not available")
        return False

    if not EXPORT_UTILS_AVAILABLE:
        print("ERROR: export_utils not available")
        return False

    try:
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Test export
        stl_data = export_shape_to_stl(box, "test_box")
        print(f"Export returned {len(stl_data)} characters (base64)")

        # Decode and check
        decoded = base64.b64decode(stl_data)
        decoded_str = decoded.decode('utf-8')

        if "export_failed" in decoded_str:
            print("ERROR: Export failed - returned error STL")
            print(f"Error STL content: {decoded_str[:200]}...")
            return False

        if "solid empty" in decoded_str:
            print("ERROR: Export returned minimal empty STL")
            return False

        print("✓ Export returned proper STL data")
        return True

    except (AttributeError, TypeError, ValueError, base64.binascii.Error) as e:
        print(f"ERROR in export test: {e}")
        traceback.print_exc()
        return False


def test_quick_execution():
    """Quick test of code execution."""
    print("\\n=== Testing Code Execution ===")

    if not SERVER_CORE_AVAILABLE:
        print("ERROR: server_core not available")
        return False

    try:
        # Simple test code
        test_code = '''
import cadquery as cq

# Create a simple box
box = cq.Workplane("XY").box(20, 20, 20)
show_object(box, "TestBox", "red")

print("Box created successfully!")
'''

        print("Running test code...")
        result = run_cadquery_code(test_code)

        if result['success']:
            print("✓ Code executed successfully")
            print(f"Objects created: {len(result['objects'])}")
            if result['output']:
                print(f"Output: {result['output']}")
            return True

        print(f"ERROR: Code execution failed: {result['error']}")
        if result.get('traceback'):
            print("Traceback:")
            print(result['traceback'])
        return False

    except (TypeError, KeyError, AttributeError) as e:
        print(f"ERROR in execution test: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all quick tests."""
    print("DazCAD Quick Diagnostic Tests")
    print("=" * 40)

    # Run tests
    library_ok = test_quick_library_loading()
    cadquery_ok = test_quick_cadquery()
    export_ok = test_quick_export()
    execution_ok = test_quick_execution()

    # Summary
    print("\\n" + "=" * 40)
    print("SUMMARY:")
    print(f"Library Loading: {'✓' if library_ok else '✗'}")
    print(f"CadQuery Basic: {'✓' if cadquery_ok else '✗'}")
    print(f"Export Function: {'✓' if export_ok else '✗'}")
    print(f"Code Execution: {'✓' if execution_ok else '✗'}")

    if all([library_ok, cadquery_ok, export_ok, execution_ok]):
        print("\\n✓ All tests passed!")
        return True

    print("\\n✗ Some tests failed - this explains your issues")
    return False


class TestQuickDiagnostics(unittest.TestCase):
    """Quick diagnostic unit tests."""

    def test_library_loading(self):
        """Test library loading functionality."""
        self.assertTrue(test_quick_library_loading())

    def test_cadquery_basic(self):
        """Test basic CadQuery functionality."""
        self.assertTrue(test_quick_cadquery())


if __name__ == "__main__":
    SUCCESS = main()
    sys.exit(0 if SUCCESS else 1)
