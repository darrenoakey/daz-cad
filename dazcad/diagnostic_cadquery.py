"""CadQuery-specific diagnostic functions."""

import traceback
import unittest

# Test CadQuery import
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False


def test_cadquery_basic():
    """Test basic CadQuery functionality."""
    if not CADQUERY_AVAILABLE:
        print("✗ CadQuery not available, skipping basic test")
        return False

    try:
        # Create a simple box
        box = cq.Workplane("XY").box(10, 10, 10)
        print("✓ Basic CadQuery box creation successful")

        # Test shape extraction
        if hasattr(box, 'val'):
            shape = box.val()
            print("✓ Shape extraction successful")

            # Test STL export
            if hasattr(shape, 'toSTL'):
                stl_data = shape.toSTL()
                print(f"✓ STL export successful: {len(stl_data)} bytes")
                return True
            print("✗ Shape doesn't have toSTL method")
            return False
        print("✗ Box doesn't have val() method")
        return False

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"✗ Basic CadQuery test failed: {e}")
        traceback.print_exc()
        return False


class TestCadQueryDiagnostics(unittest.TestCase):
    """Tests for CadQuery diagnostic functions."""

    def test_cadquery_basic_function(self):
        """Test that test_cadquery_basic function exists."""
        self.assertTrue(callable(test_cadquery_basic))
