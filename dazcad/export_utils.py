"""Export utilities for CadQuery objects to various formats."""

import unittest

# Import all export functionality from specialized modules
try:
    from .export_formats import (get_supported_formats, get_supported_export_formats,
                                get_format_by_name)
    from .export_shapes import export_shape_to_stl, export_shape_to_format
    from .export_assemblies import export_assembly_to_format
except ImportError:
    # Fallback for direct execution
    from export_formats import (get_supported_formats, get_supported_export_formats,
                               get_format_by_name)
    from export_shapes import export_shape_to_stl, export_shape_to_format
    from export_assemblies import export_assembly_to_format


class TestExportUtils(unittest.TestCase):
    """Tests for export utilities coordination."""

    def test_all_exports_available(self):
        """Test that all export functions are available."""
        self.assertTrue(callable(export_shape_to_stl))
        self.assertTrue(callable(export_shape_to_format))
        self.assertTrue(callable(export_assembly_to_format))
        self.assertTrue(callable(get_supported_formats))
        self.assertTrue(callable(get_supported_export_formats))
        self.assertTrue(callable(get_format_by_name))
