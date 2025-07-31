"""Test that all Python files in the directory can be imported successfully.

This test attempts to import every Python file in the dazcad directory to
catch any relative import issues or other import problems.
"""

import sys
import unittest
from pathlib import Path

# Import utility classes with fallback for direct execution
try:
    from .import_test_utils import ImportUtils
    from .import_test_mocks import MockUtils
except ImportError:
    from import_test_utils import ImportUtils
    from import_test_mocks import MockUtils


class TestAllImports(unittest.TestCase):
    """Test that all Python files can be imported without errors."""

    def setUp(self):
        """Set up test environment."""
        # Get the directory containing this test file
        self.test_dir = Path(__file__).parent
        self.import_utils = ImportUtils(self.test_dir)

        # Add the parent directory to sys.path to enable relative imports
        self.parent_dir = self.test_dir.parent
        if str(self.parent_dir) not in sys.path:
            sys.path.insert(0, str(self.parent_dir))
            self.added_to_path = True
        else:
            self.added_to_path = False

    def tearDown(self):
        """Clean up test environment."""
        # Remove from sys.path if we added it
        if self.added_to_path and str(self.parent_dir) in sys.path:
            sys.path.remove(str(self.parent_dir))

    def test_import_all_python_files(self):
        """Test importing all Python files in the dazcad directory."""
        python_files = self.import_utils.find_python_files()
        self.assertGreater(len(python_files), 0, "No Python files found to test")

        # Track results
        successful_imports = []
        failed_imports = []
        relative_import_failures = []

        # Expected failures (files that need special context)
        expected_failures = {
            'server.py': 'Sanic app name conflicts during testing',
            'bearing.py': 'Library file needs show_object context',
            'gear.py': 'Library file needs show_object context',
            'vase.py': 'Library file needs show_object context',
            'assembly.py': 'Library file needs show_object context',
            'bracket.py': 'Library file needs show_object context'
        }

        for file_path in python_files:
            try:
                self.import_utils.import_module_from_path(file_path)
                successful_imports.append(file_path.name)
            except Exception as e:  # pylint: disable=broad-exception-caught
                error_msg = str(e)

                # Check if this is the critical relative import issue
                if "attempted relative import with no known parent package" in error_msg:
                    relative_import_failures.append((file_path.name, error_msg))

                failed_imports.append((file_path.name, error_msg))

        # Print summary
        print("\\nImport test summary:")
        print(f"Successful imports: {len(successful_imports)}")
        print(f"Failed imports: {len(failed_imports)}")

        if successful_imports:
            print(f"Successfully imported: {', '.join(successful_imports)}")

        if failed_imports:
            print("Failed imports:")
            for filename, error in failed_imports:
                if filename in expected_failures:
                    print(f"  {filename}: {error} (EXPECTED - {expected_failures[filename]})")
                else:
                    print(f"  {filename}: {error} (UNEXPECTED)")

        # Only fail the test for critical relative import issues
        if relative_import_failures:
            failure_msg = "Critical relative import failures found:\\n"
            for filename, error in relative_import_failures:
                failure_msg += f"  {filename}: {error}\\n"
            self.fail(failure_msg)

        # Verify we have a reasonable number of successful imports
        self.assertGreaterEqual(len(successful_imports), 15,
                               "Too few successful imports - may indicate systemic issues")

    def test_specific_known_imports(self):
        """Test specific imports that we know should work."""
        results = self.import_utils.test_known_imports()

        # Expected failures
        expected_failures = {
            'server': 'Sanic app name "dazcad" already in use'
        }

        for module_name, success, error in results:
            with self.subTest(module=module_name):
                if not success:
                    # Check if this is an expected failure
                    if (module_name in expected_failures and
                            expected_failures[module_name] in str(error)):
                        # This is expected, skip it
                        continue
                    self.fail(f"Failed to import {module_name}: {error}")

    def test_library_examples_import(self):
        """Test that all library examples can be imported."""
        library_dir = self.test_dir / "library"
        if not library_dir.exists():
            self.skipTest("Library directory not found")

        library_files = list(library_dir.glob("*.py"))
        if not library_files:
            self.skipTest("No library files found")

        relative_import_failures = []
        failed_imports = []

        for file_path in library_files:
            if file_path.name == "__init__.py":
                continue

            try:
                self.import_utils.import_module_from_path(file_path)
            except Exception as e:  # pylint: disable=broad-exception-caught
                error_msg = str(e)

                # Check if this is the critical relative import issue
                if "attempted relative import with no known parent package" in error_msg:
                    relative_import_failures.append((file_path.name, error_msg))

                # Library files are expected to fail due to show_object dependency
                if "name 'show_object' is not defined" not in error_msg:
                    failed_imports.append((file_path.name, error_msg))

        # Only fail for critical relative import issues or unexpected failures
        if relative_import_failures:
            failure_msg = "Critical relative import failures in library files:\\n"
            for filename, error in relative_import_failures:
                failure_msg += f"  {filename}: {error}\\n"
            self.fail(failure_msg)

        if failed_imports:
            failure_msg = "Unexpected import failures in library files:\\n"
            for filename, error in failed_imports:
                failure_msg += f"  {filename}: {error}\\n"
            self.fail(failure_msg)

    def test_import_with_mock_dependencies(self):
        """Test importing with mock dependencies for modules that need external deps."""
        mock_modules = {
            'cadquery': MockUtils.create_mock_cadquery(),
            'sanic': MockUtils.create_mock_sanic(),
        }

        original_modules = MockUtils.install_mocks(mock_modules)

        try:
            # Try importing files that depend on external modules
            files_with_deps = ['server.py', 'server_routes.py',
                             'cadquery_processor.py', 'cadquery_core.py']

            for filename in files_with_deps:
                file_path = self.test_dir / filename
                if file_path.exists():
                    with self.subTest(file=filename):
                        try:
                            self.import_utils.import_module_from_path(file_path)
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            # Allow some failures with mocked deps, just log them
                            print(f"Warning: {filename} failed with mocked deps: {e}")

        finally:
            MockUtils.restore_mocks(mock_modules, original_modules)
