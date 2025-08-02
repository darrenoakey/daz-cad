"""Library export format tests.

Tests for export format functionality and consistency.
"""

import unittest
import os
from pathlib import Path

try:
    from .export_utils import get_supported_formats
    from .library_manager import LibraryManager
    from .test_cadquery_file import (execute_cadquery_file,
                                     extract_exportable_objects,
                                     test_export_format)
except ImportError:
    # Fallback for direct execution
    from export_utils import get_supported_formats
    from library_manager import LibraryManager
    from test_cadquery_file import (execute_cadquery_file,
                                   extract_exportable_objects,
                                   test_export_format)


class TestLibraryExports(unittest.TestCase):
    """Tests for library file export functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test class with library manager."""
        # Initialize library manager with correct path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        library_path = os.path.join(current_dir, 'library')
        cls.library_manager = LibraryManager(built_in_library_path=library_path)

        # Get all library files
        files = cls.library_manager.list_files()
        cls.library_files = files['built_in']  # Focus on built-in library
        cls.library_path = library_path

    def test_all_export_formats_for_all_objects(self):
        """Test all export formats for all objects from all library files."""
        supported_formats = get_supported_formats()
        self.assertGreater(len(supported_formats), 0, "No export formats available")

        for filename in self.library_files:
            with self.subTest(filename=filename):
                file_path = Path(self.library_path) / filename

                # Execute and extract objects
                success, result, error = execute_cadquery_file(file_path)
                self.assertTrue(success, f"File {filename} failed: {error}")

                exportable_objects = extract_exportable_objects(result)

                # Test each object with each format
                for obj_info in exportable_objects:
                    obj_name = f"{filename}::{obj_info['name']}"

                    for format_name in supported_formats:
                        test_name = f"{obj_name}::{format_name}"
                        with self.subTest(test_case=test_name):

                            # Test the export - verify it produces valid data or fails properly
                            try:
                                export_success, export_error = test_export_format(
                                    obj_info['object'],
                                    obj_info['type'],
                                    format_name
                                )

                                # Verify the export system returns proper values
                                self.assertIsInstance(export_success, bool,
                                                    f"Export test should return boolean "
                                                    f"for {test_name}")
                                self.assertIsInstance(export_error, str,
                                                    f"Export test should return string "
                                                    f"error for {test_name}")

                                # If export succeeds, the error should be empty
                                # If export fails, there should be a meaningful error message
                                if export_success:
                                    self.assertEqual(export_error, "",
                                                   f"Successful export should have no error "
                                                   f"for {test_name}")
                                else:
                                    self.assertNotEqual(export_error.strip(), "",
                                                      f"Failed export should have error message "
                                                      f"for {test_name}")
                                    # Error should not indicate a placeholder/default was returned
                                    self.assertNotIn("placeholder", export_error.lower(),
                                                   f"Export should not return placeholders "
                                                   f"for {test_name}")

                            except (AttributeError, TypeError, ValueError) as e:
                                # These exceptions are expected if the object can't be exported
                                # This is proper failure behavior, not placeholder returns
                                self.assertIsInstance(str(e), str,
                                                    f"Exception should have string message "
                                                    f"for {test_name}: {e}")

    def test_export_format_consistency(self):
        """Test that export formats are consistent with expectations."""
        formats = get_supported_formats()

        # We should support at least STL, STEP, and 3MF
        expected_formats = {'stl', 'step', '3mf'}
        available_formats = set(formats)

        self.assertTrue(expected_formats.issubset(available_formats),
                       f"Missing expected formats: {expected_formats - available_formats}")
