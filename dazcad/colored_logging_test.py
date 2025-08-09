"""Tests for colored logging utilities."""

import unittest
import sys
from io import StringIO

try:
    from .colored_logging import (
        log_server_call, log_input, log_output, log_error, 
        log_success, log_debug, log_library_operation
    )
except ImportError:
    # Fallback for direct execution
    from colored_logging import (
        log_server_call, log_input, log_output, log_error,
        log_success, log_debug, log_library_operation
    )


class TestColoredLogging(unittest.TestCase):
    """Tests for colored logging utilities."""

    def setUp(self):
        """Set up test fixtures."""
        # Capture stdout to test logging output
        self.original_stdout = sys.stdout
        self.captured_output = StringIO()
        sys.stdout = self.captured_output

    def tearDown(self):
        """Clean up test fixtures."""
        sys.stdout = self.original_stdout

    def test_log_server_call_basic(self):
        """Test basic server call logging."""
        log_server_call("/test")
        output = self.captured_output.getvalue()
        self.assertIn("SERVER CALL", output)
        self.assertIn("/test", output)
        self.assertIn("GET", output)  # Default method

    def test_log_server_call_with_method(self):
        """Test server call logging with custom method."""
        log_server_call("/test", "POST")
        output = self.captured_output.getvalue()
        self.assertIn("SERVER CALL", output)
        self.assertIn("/test", output)
        self.assertIn("POST", output)

    def test_log_input_string(self):
        """Test input logging with string data."""
        log_input("test", "string value")
        output = self.captured_output.getvalue()
        self.assertIn("INPUT test:", output)
        self.assertIn("string value", output)

    def test_log_input_truncation(self):
        """Test that long input is truncated."""
        long_string = "x" * 300
        log_input("test", long_string, max_length=50)
        output = self.captured_output.getvalue()
        self.assertIn("...", output)

    def test_log_output_basic(self):
        """Test basic output logging."""
        log_output("test", "output data")
        output = self.captured_output.getvalue()
        self.assertIn("OUTPUT test:", output)
        self.assertIn("output data", output)

    def test_log_error_basic(self):
        """Test error logging."""
        log_error("test", "error message")
        output = self.captured_output.getvalue()
        self.assertIn("ERROR test:", output)
        self.assertIn("error message", output)

    def test_log_success_basic(self):
        """Test success logging."""
        log_success("test", "success message")
        output = self.captured_output.getvalue()
        self.assertIn("SUCCESS test:", output)
        self.assertIn("success message", output)

    def test_log_debug_basic(self):
        """Test debug logging."""
        log_debug("test", "debug message")
        output = self.captured_output.getvalue()
        self.assertIn("DEBUG test:", output)
        self.assertIn("debug message", output)

    def test_log_library_operation_basic(self):
        """Test library operation logging."""
        log_library_operation("TEST_OP", "operation details")
        output = self.captured_output.getvalue()
        self.assertIn("LIBRARY TEST_OP:", output)
        self.assertIn("operation details", output)

    def test_logging_functions_include_brackets(self):
        """Test that logging functions include timestamp brackets."""
        log_error("test", "error")
        output = self.captured_output.getvalue()
        # Check for timestamp brackets
        self.assertIn("[", output)
        self.assertIn("]", output)

    def test_logging_doesnt_crash_with_none_data(self):
        """Test that logging functions handle None data gracefully."""
        # These should not crash
        log_input("test", None)
        log_output("test", None)
        log_debug("test", None)
        # Just verify we got some output
        output = self.captured_output.getvalue()
        self.assertGreater(len(output), 0)


if __name__ == "__main__":
    unittest.main()
