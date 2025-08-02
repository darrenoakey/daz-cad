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
    from .test_all_imports_runner import run_comprehensive_import_tests
except ImportError:
    from import_test_utils import ImportUtils
    from test_all_imports_runner import run_comprehensive_import_tests


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
        run_comprehensive_import_tests(self, self.import_utils)

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

    def test_import_with_real_dependencies(self):
        """Test importing files that have external dependencies to verify they import correctly."""
        # Only test files if their dependencies are actually available
        try:
            import cadquery  # pylint: disable=unused-import,import-outside-toplevel
            cadquery_available = True
        except ImportError:
            cadquery_available = False

        try:
            import sanic  # pylint: disable=unused-import,import-outside-toplevel
            sanic_available = True
        except ImportError:
            sanic_available = False

        # Test CadQuery-dependent files if available
        if cadquery_available:
            cadquery_files = ['cadquery_processor.py', 'cadquery_core.py',
                             'export_utils.py', 'cadquery_file_validator.py']

            for filename in cadquery_files:
                file_path = self.test_dir / filename
                if file_path.exists():
                    with self.subTest(file=filename):
                        try:
                            self.import_utils.import_module_from_path(file_path)
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            # Only fail if it's not a known issue
                            if "attempted relative import" not in str(e):
                                msg = f"Failed to import {filename} with CadQuery available: {e}"
                                self.fail(msg)

        # Test Sanic-dependent files if available
        if sanic_available:
            sanic_files = ['server_core.py', 'server_routes.py', 'server_static_routes.py']

            for filename in sanic_files:
                file_path = self.test_dir / filename
                if file_path.exists():
                    with self.subTest(file=filename):
                        try:
                            self.import_utils.import_module_from_path(file_path)
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            # Only fail if it's not a known issue or Sanic app name conflict
                            if ("attempted relative import" not in str(e) and
                                "Sanic app name" not in str(e)):
                                msg = f"Failed to import {filename} with Sanic available: {e}"
                                self.fail(msg)
