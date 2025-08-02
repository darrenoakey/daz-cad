"""Export utilities tests.

Tests for export format functionality.
"""

import unittest

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .export_utils import export_assembly_to_format
except ImportError:
    # Fallback for direct execution
    from export_utils import export_assembly_to_format


class TestExportUtils(unittest.TestCase):
    """Tests for export utilities."""

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_export_assembly_to_format_real(self):
        """Test assembly export to different formats with real CadQuery assemblies."""
        # Create a simple assembly with two parts
        box1 = cq.Workplane("XY").box(10, 10, 10)
        box2 = cq.Workplane("XY").box(5, 5, 20)

        # Create assembly without location for now to avoid constructor issues
        assembly = cq.Assembly()
        assembly.add(box1, name="box1")
        assembly.add(box2, name="box2")

        # Test STL export
        stl_data = export_assembly_to_format(assembly, 'stl')
        self.assertIsInstance(stl_data, bytes)
        self.assertGreater(len(stl_data), 100)  # Assembly should be larger

        # Test STEP export
        step_data = export_assembly_to_format(assembly, 'step')
        self.assertIsInstance(step_data, bytes)
        self.assertGreater(len(step_data), 100)
