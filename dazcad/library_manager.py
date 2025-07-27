"""Library manager for DazCAD - handles example libraries and user library with git integration."""

import unittest

# Import core functionality
try:
    from .library_manager_core import LibraryManager
except ImportError:
    # Fallback for direct execution
    from library_manager_core import LibraryManager

# Re-export LibraryManager for backward compatibility
__all__ = ['LibraryManager']


class TestLibraryManagerModule(unittest.TestCase):
    """Tests for library manager module."""

    def test_library_manager_import(self):
        """Test that LibraryManager can be imported."""
        self.assertTrue(hasattr(LibraryManager, '__init__'))
        self.assertTrue(hasattr(LibraryManager, 'list_files'))
        self.assertTrue(hasattr(LibraryManager, 'save_file'))

    def test_module_exports(self):
        """Test that module exports the expected symbols."""
        self.assertIn('LibraryManager', __all__)
