"""Basic library management tests.

Tests for library file enumeration and basic library manager functionality.
"""

import unittest
import os

try:
    from .library_manager import LibraryManager
except ImportError:
    # Fallback for direct execution
    from library_manager import LibraryManager


class TestLibraryBasic(unittest.TestCase):
    """Basic tests for library management functionality."""

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

    def test_minimum_library_files(self):
        """Test that we have at least 3 library files."""
        self.assertGreaterEqual(len(self.library_files), 3,
                               f"Expected at least 3 library files, found "
                               f"{len(self.library_files)}: {self.library_files}")

    def test_library_manager_integration(self):
        """Test that library manager properly lists library files."""
        files = self.library_manager.list_files()

        # Check structure
        self.assertIsInstance(files, dict)
        self.assertIn('built_in', files)
        self.assertIn('user', files)

        # Check built-in files
        built_in_files = files['built_in']
        self.assertIsInstance(built_in_files, list)
        self.assertGreater(len(built_in_files), 0, "No built-in library files found")

        # Check that all files are Python files
        for filename in built_in_files:
            self.assertTrue(filename.endswith('.py'),
                           f"Non-Python file found in library: {filename}")
            self.assertFalse(filename.startswith('__'),
                           f"Private Python file found in library: {filename}")
