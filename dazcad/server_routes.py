"""Sanic route handlers for DazCAD server."""

import unittest

# Import all route handlers from their specialized modules
try:
    from .server_routes_code import run_code
    from .server_routes_download import download_format
    from .server_routes_chat import chat_with_ai
    from .server_routes_library import (list_library_files, get_library_file,
                                      save_library_file, create_library_file)
    from .server_core import library_manager
except ImportError:
    # Fallback for direct execution
    from server_routes_code import run_code
    from server_routes_download import download_format
    from server_routes_chat import chat_with_ai
    from server_routes_library import (list_library_files, get_library_file,
                                     save_library_file, create_library_file)
    from server_core import library_manager


class TestRoutes(unittest.TestCase):
    """Tests for route handlers."""

    def test_route_functions_exist(self):
        """Test that route functions exist."""
        self.assertTrue(callable(run_code))
        self.assertTrue(callable(download_format))
        self.assertTrue(callable(chat_with_ai))
        self.assertTrue(callable(list_library_files))
        self.assertTrue(callable(get_library_file))
        self.assertTrue(callable(save_library_file))
        self.assertTrue(callable(create_library_file))

    def test_library_manager_access(self):
        """Test that library manager is accessible."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))
