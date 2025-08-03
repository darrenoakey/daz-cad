"""Sanic server for DazCAD - main entry point and route registration."""

import sys
import unittest

# Import server components
try:
    from .server_app import app
    from .server_startup import start_server
    from .server_utils import parse_arguments
    from .server_core import library_manager
except ImportError:
    # Fallback for direct execution
    from server_app import app
    from server_startup import start_server
    from server_utils import parse_arguments
    from server_core import library_manager


class ServerTests(unittest.TestCase):
    """Tests for server functionality - see test_server.py for full test suite."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        # Basic test for module imports - full tests are in test_server.py
        self.assertTrue(hasattr(sys.modules[__name__], 'app'))
        self.assertIsNotNone(app)

    def test_parse_arguments_default(self):
        """Test argument parsing with defaults"""
        # Save original sys.argv
        original_argv = sys.argv
        try:
            # Test with no arguments
            sys.argv = ['server.py']
            parsed_args = parse_arguments()
            self.assertEqual(parsed_args.model, 'ollama:mixtral:8x7b')
            self.assertEqual(parsed_args.host, '127.0.0.1')
            self.assertEqual(parsed_args.port, 8000)
            self.assertFalse(parsed_args.debug)
            self.assertFalse(parsed_args.auto_port)
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def test_library_manager_exists(self):
        """Test that library manager is initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))


if __name__ == "__main__":
    start_server()
