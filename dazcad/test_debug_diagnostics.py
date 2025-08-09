"""Tests for debug diagnostics module."""

import unittest

try:
    from .debug_diagnostics import (
        run_diagnostics,
        test_cadquery_basic,
        test_library_manager,
        test_export_functionality,
        test_library_file_execution
    )
except ImportError:
    # Fallback for direct execution
    from debug_diagnostics import (
        run_diagnostics,
        test_cadquery_basic,
        test_library_manager,
        test_export_functionality,
        test_library_file_execution
    )


class TestDiagnostics(unittest.TestCase):
    """Tests for diagnostic functions."""

    def test_diagnostic_functions_exist(self):
        """Test that diagnostic functions exist."""
        self.assertTrue(callable(test_cadquery_basic))
        self.assertTrue(callable(test_library_manager))
        self.assertTrue(callable(test_export_functionality))
        self.assertTrue(callable(test_library_file_execution))

    def test_run_diagnostics(self):
        """Test that run_diagnostics can be called."""
        # Just test that it doesn't crash
        try:
            run_diagnostics()
        except Exception:  # pylint: disable=broad-exception-caught
            self.fail("run_diagnostics() raised an exception")


if __name__ == "__main__":
    unittest.main()
