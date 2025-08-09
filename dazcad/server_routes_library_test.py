"""Tests for library route handlers."""

import unittest

try:
    from .server_routes_library import (
        list_library_files,
        get_library_file,
        save_library_file,
        create_library_file
    )
    from .server_core import library_manager
except ImportError:
    # Fallback for direct execution
    from server_routes_library import (
        list_library_files,
        get_library_file,
        save_library_file,
        create_library_file
    )
    from server_core import library_manager


class TestLibraryRoutes(unittest.TestCase):
    """Tests for library route handlers."""

    def test_library_route_functions_exist(self):
        """Test that library route functions have expected attributes."""
        # Test function names and docstrings instead of calling them directly
        self.assertEqual(list_library_files.__name__, 'list_library_files')
        self.assertEqual(get_library_file.__name__, 'get_library_file')
        self.assertEqual(save_library_file.__name__, 'save_library_file')
        self.assertEqual(create_library_file.__name__, 'create_library_file')
        
        # Test that they have docstrings
        self.assertIsNotNone(list_library_files.__doc__)
        self.assertIsNotNone(get_library_file.__doc__)
        self.assertIsNotNone(save_library_file.__doc__)
        self.assertIsNotNone(create_library_file.__doc__)

    def test_library_manager_access(self):
        """Test that library manager is accessible."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))


if __name__ == '__main__':
    unittest.main()
