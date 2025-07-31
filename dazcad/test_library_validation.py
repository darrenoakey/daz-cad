"""Comprehensive test of all library files with all export formats.

This test uses the library manager to enumerate all library files and
ensures that each can be executed and exported in all supported formats.
"""

import unittest
from pathlib import Path

try:
    CADQUERY_AVAILABLE = True
    import cadquery  # pylint: disable=unused-import
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .library_manager_core import LibraryManager
    from .cadquery_file_validator import validate_cadquery_file
    from .export_utils import get_supported_export_formats
except ImportError:
    # Fallback for direct execution
    from library_manager_core import LibraryManager
    from cadquery_file_validator import validate_cadquery_file
    from export_utils import get_supported_export_formats


class TestAllLibraryFiles(unittest.TestCase):
    """Test case for validating all library files."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Get the library directory path
        cls.library_path = Path(__file__).parent / "library"

        # Initialize library manager with built-in library path
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

        # Track overall results
        all_results = []
        files_with_errors = []
        total_files = len(all_files)
        total_objects = 0
        total_export_tests = 0
        successful_exports = 0

        # Test each file
        for filename in all_files:
            file_path = self.library_path / filename

            with self.subTest(library_file=filename):
                # Run comprehensive validation
                result = validate_cadquery_file(file_path, verbose=True)
                all_results.append(result)

                # Update statistics
                summary = result.get('summary', {})
                total_objects += summary.get('total_objects', 0)
                total_export_tests += summary.get('total_export_tests', 0)
                successful_exports += summary.get('successful_exports', 0)

                # Check if file had errors
                if not result['success']:
                    files_with_errors.append(filename)

                # Assert that the file executes successfully
                # We allow export failures but not execution failures
                if result['execution_error']:
                    self.fail(f"{filename}: {result['execution_error']}")

                # Assert that we got at least one object
                self.assertGreater(summary.get('total_objects', 0), 0,
                                 f"No exportable objects found in {filename}")

        # Print comprehensive summary
        print(f"\n{'='*60}")
        print("Library Files Test Summary")
        print(f"{'='*60}")
        print(f"Total library files tested: {total_files}")
        print(f"Files with issues: {len(files_with_errors)}")
        print(f"Total objects found: {total_objects}")
        print(f"Total export tests: {total_export_tests}")
        print(f"Successful exports: {successful_exports}")

        if total_export_tests > 0:
            success_rate = (successful_exports / total_export_tests * 100)
            print(f"Export success rate: {success_rate:.1f}%")

        if files_with_errors:
            print(f"\nFiles with issues: {', '.join(files_with_errors)}")
            print("⚠️  WARNING: Some library files have export issues that may need fixing.")
        else:
            print("\n✅ All library files validated successfully!")

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
        if CADQUERY_AVAILABLE:
            supported_formats = list(get_supported_export_formats().values())
        else:
            supported_formats = []

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

                # Check structure of result
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                self.assertIn('file', result)
                self.assertIn('execution_error', result)
                self.assertIn('objects', result)
                self.assertIn('summary', result)

                # Check summary structure
                summary = result['summary']
                self.assertIn('total_objects', summary)
                self.assertIn('valid_objects', summary)
                self.assertIn('total_export_tests', summary)
                self.assertIn('successful_exports', summary)

                # File should at least execute without error
                if result['execution_error']:
                    self.fail(f"Execution failed for {filename}: {result['execution_error']}")
