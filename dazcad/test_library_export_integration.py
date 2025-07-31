"""Integration tests for library export functionality."""

import unittest
import os

try:
    from .export_utils import get_supported_formats
except ImportError:
    from export_utils import get_supported_formats


class TestLibraryExportIntegration(unittest.TestCase):
    """Integration tests for library export functionality."""

    def test_specific_library_files(self):
        """Test specific known library files."""
        # Get library path
        library_path = os.path.join(os.path.dirname(__file__), 'library')

        # Test that expected files exist
        expected_files = ['bearing.py', 'gear.py', 'vase.py', 'assembly.py', 'bracket.py']
        for filename in expected_files:
            file_path = os.path.join(library_path, filename)
            self.assertTrue(os.path.exists(file_path),
                          f"Expected library file {filename} not found")

    def test_export_format_consistency(self):
        """Test that export formats are consistent with what we expect."""
        formats = get_supported_formats()

        # We should support at least STL, STEP, and 3MF
        expected_formats = {'stl', 'step', '3mf'}
        available_formats = set(formats)

        self.assertTrue(expected_formats.issubset(available_formats),
                       f"Missing expected formats: {expected_formats - available_formats}")
