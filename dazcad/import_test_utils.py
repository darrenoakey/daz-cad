"""Import helper utilities for testing."""

import importlib
import importlib.util
import sys
from pathlib import Path


class ImportUtils:
    """Utility class for import testing operations."""

    def __init__(self, test_dir):
        """Initialize with test directory."""
        self.test_dir = test_dir

    def import_module_from_path(self, file_path):
        """Import a module from a file path.

        Args:
            file_path: Path to the Python file to import

        Raises:
            Various import-related exceptions if import fails
        """
        # Convert path to module name
        relative_path = file_path.relative_to(self.test_dir)

        # Create module name
        if relative_path.parent.name == "library":
            module_name = f"dazcad.library.{relative_path.stem}"
        else:
            module_name = f"dazcad.{relative_path.stem}"

        # Try to import using importlib
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                raise ImportError(f"Could not create spec for {module_name}")

            module = importlib.util.module_from_spec(spec)
            if module is None:
                raise ImportError(f"Could not create module for {module_name}")

            # Add to sys.modules to handle relative imports
            sys.modules[module_name] = module

            # Execute the module
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            # Clean up from sys.modules if we added it
            if module_name in sys.modules:
                del sys.modules[module_name]
            raise e

    def find_python_files(self):
        """Find all Python files to test."""
        python_files = []

        # Check current directory
        for file_path in self.test_dir.glob("*.py"):
            if file_path.name not in ('__init__.py', 'test_all_imports.py'):
                python_files.append(file_path)

        # Check library subdirectory
        library_dir = self.test_dir / "library"
        if library_dir.exists():
            for file_path in library_dir.glob("*.py"):
                if file_path.name != "__init__.py":
                    python_files.append(file_path)

        return python_files

    def test_known_imports(self):
        """Test specific imports that we know should work."""
        known_modules = [
            'server', 'server_core', 'server_routes', 'download_handler',
            'export_utils', 'library_manager', 'library_manager_git', 
            'llm_chat', 'llm_core'
        ]

        results = []
        for module_name in known_modules:
            try:
                # Try both relative and absolute import
                try:
                    # Try relative import first
                    module = importlib.import_module(f".{module_name}", package="dazcad")
                except (ImportError, ValueError):
                    # Fallback to absolute import
                    module = importlib.import_module(f"dazcad.{module_name}")

                if module is not None:
                    results.append((module_name, True, None))
                else:
                    results.append((module_name, False, "Module is None"))

            except ImportError as e:
                results.append((module_name, False, str(e)))

        return results
