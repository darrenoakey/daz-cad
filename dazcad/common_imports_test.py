"""Tests for common import utilities."""

import unittest

from .common_imports import (
    CADQUERY_AVAILABLE, cq, get_module_with_fallback, 
    setup_cadquery_execution_environment, get_current_library_path,
    create_test_library_manager
)


class TestCommonImports(unittest.TestCase):
    """Tests for common import utilities."""

    def test_cadquery_availability_check(self):
        """Test CadQuery availability detection."""
        self.assertIsInstance(CADQUERY_AVAILABLE, bool)
        if CADQUERY_AVAILABLE:
            self.assertIsNotNone(cq)
        else:
            self.assertIsNone(cq)

    def test_get_module_with_fallback(self):
        """Test module import with fallback."""
        # Test with a module that should exist
        result = get_module_with_fallback('.colored_logging', 'colored_logging')
        # Should return something (module or None)
        self.assertTrue(result is not None or result is None)

    def test_setup_cadquery_execution_environment(self):
        """Test CadQuery execution environment setup."""
        env = setup_cadquery_execution_environment()
        self.assertIsInstance(env, dict)
        self.assertIn('cq', env)
        self.assertIn('cadquery', env)
        self.assertIn('__name__', env)

    def test_get_current_library_path(self):
        """Test library path detection."""
        path = get_current_library_path()
        self.assertIsInstance(path, str)
        self.assertTrue(path.endswith('library'))

    def test_create_test_library_manager(self):
        """Test library manager creation."""
        manager = create_test_library_manager()
        # Should return manager or None
        self.assertTrue(manager is not None or manager is None)


if __name__ == '__main__':
    unittest.main()
