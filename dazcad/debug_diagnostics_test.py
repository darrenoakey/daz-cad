"""Tests for debug diagnostics module."""

import unittest

try:
    from .debug_diagnostics import run_diagnostics
except ImportError:
    # Fallback for direct execution
    from debug_diagnostics import run_diagnostics


class TestDiagnostics(unittest.TestCase):
    """Tests for diagnostic functions."""

    def test_run_diagnostics_executes_without_error(self):
        """Test that run_diagnostics can be executed without crashing."""
        # This should execute without raising exceptions
        # We don't test the output since it prints to stdout
        try:
            run_diagnostics()
            # If we get here, the function executed successfully
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"run_diagnostics() raised an exception: {e}")

    def test_run_diagnostics_returns_none(self):
        """Test that run_diagnostics returns None (it's a procedure)."""
        result = run_diagnostics()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
