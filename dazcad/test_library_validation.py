"""Comprehensive test of all library files with all export formats.

This test uses the library manager to enumerate all library files and
ensures that each can be executed and exported in all supported formats.
"""
# pylint: disable=import-outside-toplevel,too-many-locals,too-many-branches

import unittest
from pathlib import Path

try:
    from .common_imports import CADQUERY_AVAILABLE, create_test_library_manager
    from .validation_patterns import check_common_validation_assertions
    from .cadquery_file_validator import validate_cadquery_file
    from .export_utils import get_supported_export_formats
    from .test_library_validation_runner import run_comprehensive_validation
except ImportError:
    # Fallback for direct execution
    from common_imports import CADQUERY_AVAILABLE, create_test_library_manager
    from validation_patterns import check_common_validation_assertions
    from cadquery_file_validator import validate_cadquery_file
    from export_utils import get_supported_export_formats
    from test_library_validation_runner import run_comprehensive_validation


class TestAllLibraryFiles(unittest.TestCase):
    """Test case for validating all library files."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Get the library directory path
        cls.library_path = Path(__file__).parent / "library"

        # Initialize library manager using common patterns
        cls.library_manager = create_test_library_manager()
        if cls.library_manager is None:
            # Fallback initialization
            from .library_manager_core import LibraryManager
            cls.library_manager = LibraryManager(
                built_in_library_path=str(cls.library_path),
                user_library_path=None  # We're only testing built-in libraries
            )

    def test_minimum_library_files_requirement(self):
        """Test that we have at least 3 library files."""
        library_files = self.library_manager.list_files()
        all_files = library_files.get('built_in', [])

        self.assertGreaterEqual(len(all_files), 3,
                               f"Library must contain at least 3 files, found {len(all_files)}: "
                               f"{', '.join(all_files)}")

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_all_library_files_comprehensive(self):
        """Test all library files for execution and export in all formats."""
        # Get list of library files using library manager
        library_files = self.library_manager.list_files()
        all_files = library_files.get('built_in', [])

        # Ensure we have at least 3 library files
        self.assertGreaterEqual(len(all_files), 3,
                               f"Expected at least 3 library files, found {len(all_files)}")

        # Run comprehensive validation
        run_comprehensive_validation(all_files, self.library_path, self)

    def test_library_manager_functionality(self):
        """Test that library manager works correctly."""
        # List files
        files = self.library_manager.list_files()
        self.assertIsInstance(files, dict)
        self.assertIn('built_in', files)
        self.assertIsInstance(files['built_in'], list)

        # Check that we can load a file if any exist
        if files['built_in']:
            first_file = files['built_in'][0]
            content = self.library_manager.get_file_content(first_file)
            self.assertIsInstance(content, str)
            self.assertGreater(len(content), 0)

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_export_formats_available(self):
        """Test that we have export formats available."""
        supported_formats = list(get_supported_export_formats().values())

        self.assertGreater(len(supported_formats), 0,
                          "No export formats available")

        format_names = [fmt.extension for fmt in supported_formats]
        self.assertIn('stl', format_names, "STL format should be available")
        self.assertIn('step', format_names, "STEP format should be available")

    @unittest.skipIf(not CADQUERY_AVAILABLE, "CadQuery not available")
    def test_individual_library_file_validation(self):
        """Test validation function on each library file individually."""
        library_files = self.library_manager.list_files()
        all_files = library_files.get('built_in', [])

        for filename in all_files:
            file_path = self.library_path / filename

            with self.subTest(library_file=filename):
                # Validate file
                result = validate_cadquery_file(file_path, verbose=False)

                # Use common validation assertions
                check_common_validation_assertions(self, result)

                # File should at least execute without error
                if result['execution_error']:
                    self.fail(f"Execution failed for {filename}: {result['execution_error']}")
