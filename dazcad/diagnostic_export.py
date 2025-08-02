"""Export functionality diagnostic functions."""

import base64
import traceback
import unittest

# Import dependencies
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .export_utils import export_shape_to_stl
except ImportError:
    try:
        from export_utils import export_shape_to_stl
    except ImportError:
        export_shape_to_stl = None


def test_export_functionality():
    """Test export functionality."""
    if not CADQUERY_AVAILABLE or export_shape_to_stl is None:
        print("✗ Prerequisites not met for export test")
        return False

    try:
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)

        # Test export
        stl_data = export_shape_to_stl(box, "test_box")
        print(f"✓ Export successful: {len(stl_data)} characters (base64)")

        # Decode and check if it's the minimal STL
        decoded = base64.b64decode(stl_data)
        decoded_str = decoded.decode('utf-8')

        if "solid empty" in decoded_str:
            print("✗ Export returned minimal empty STL - indicates failure")
            return False
        print("✓ Export returned proper STL data")
        return True

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"✗ Export test failed: {e}")
        traceback.print_exc()
        return False


class TestExportDiagnostics(unittest.TestCase):
    """Tests for export diagnostic functions."""

    def test_export_functionality_exists(self):
        """Test that test_export_functionality function exists."""
        self.assertTrue(callable(test_export_functionality))
