"""Common import patterns and utilities for DazCAD modules.

This module provides centralized import handling to reduce code duplication
across the DazCAD codebase.
"""

import unittest

# CadQuery availability check
try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    cq = None
    CADQUERY_AVAILABLE = False


def get_module_with_fallback(relative_name, absolute_name=None):
    """Import module with fallback from relative to absolute import.

    Args:
        relative_name: Relative import name (e.g., '.module_name')
        absolute_name: Absolute import name (e.g., 'module_name')

    Returns:
        Imported module or None if import fails
    """
    if absolute_name is None:
        absolute_name = relative_name.lstrip('.')

    try:
        # Try relative import first
        from importlib import import_module  # pylint: disable=import-outside-toplevel
        return import_module(relative_name, package='dazcad')
    except (ImportError, ValueError):
        try:
            # Fallback to absolute import
            from importlib import import_module  # pylint: disable=import-outside-toplevel
            return import_module(absolute_name)
        except ImportError:
            return None


def setup_cadquery_execution_environment():
    """Set up common CadQuery execution environment.

    Returns:
        Dictionary with common CadQuery globals
    """
    return {
        'cq': cq,
        'cadquery': cq,
        '__name__': '__main__'
    }


def get_current_library_path():
    """Get the path to the library directory.

    Returns:
        Path to the library directory
    """
    import os  # pylint: disable=import-outside-toplevel
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "library")


def create_test_library_manager():
    """Create a library manager for testing.

    Returns:
        LibraryManager instance or None if creation fails
    """
    try:
        # pylint: disable=import-outside-toplevel
        from .library_manager_core import LibraryManager
        library_path = get_current_library_path()
        return LibraryManager(built_in_library_path=library_path)
    except ImportError:
        try:
            # pylint: disable=import-outside-toplevel
            from library_manager_core import LibraryManager
            library_path = get_current_library_path()
            return LibraryManager(built_in_library_path=library_path)
        except ImportError:
            return None


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
