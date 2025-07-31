"""
Tests for server_utils module.
"""

import unittest
import sys

try:
    from .server_utils import is_port_available, find_available_port, parse_arguments
except ImportError:
    # Fallback for direct execution
    from server_utils import is_port_available, find_available_port, parse_arguments


class TestServerUtils(unittest.TestCase):
    """Tests for server utility functions."""

    def test_is_port_available(self):
        """Test port availability checking."""
        # Test with a port that should be available
        self.assertTrue(is_port_available('127.0.0.1', 65432))

        # Test with invalid host (should return False)
        self.assertFalse(is_port_available('invalid-host', 8000))

    def test_find_available_port(self):
        """Test finding available ports."""
        # Test find_available_port function
        test_port = find_available_port('127.0.0.1', 8000, 8010)
        self.assertIsNotNone(test_port)
        self.assertGreaterEqual(test_port, 8000)
        self.assertLessEqual(test_port, 8010)

        # Test with invalid host (should return None)
        result = find_available_port('invalid-host', 8000, 8001)
        self.assertIsNone(result)

    def test_parse_arguments(self):
        """Test argument parsing with defaults."""
        # Save original sys.argv
        original_argv = sys.argv
        try:
            # Test with no arguments
            sys.argv = ['server_utils.py']
            parsed_args = parse_arguments()
            self.assertEqual(parsed_args.model, 'ollama:mixtral:8x7b')
            self.assertEqual(parsed_args.host, '127.0.0.1')
            self.assertEqual(parsed_args.port, 8000)
            self.assertFalse(parsed_args.debug)
            self.assertFalse(parsed_args.auto_port)
        finally:
            # Restore original sys.argv
            sys.argv = original_argv
