"""Tests for library manager module."""

import unittest

from .library_manager import LibraryManager


class TestLibraryManagerModule(unittest.TestCase):
    """Tests for library manager module."""

    def test_library_manager_import(self):
        """Test that LibraryManager can be imported."""
        self.assertTrue(hasattr(LibraryManager, '__init__'))
        self.assertTrue(hasattr(LibraryManager, 'list_files'))
        self.assertTrue(hasattr(LibraryManager, 'save_file'))

    def test_module_exports(self):
        """Test that module exports the expected symbols."""
        from . import library_manager
        self.assertIn('LibraryManager', library_manager.__all__)


if __name__ == '__main__':
    unittest.main()
