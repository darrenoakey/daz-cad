"""Tests for common export patterns."""

import unittest

try:
    from .export_patterns import (
        safe_export_with_cleanup, validate_export_result, create_test_export_object
    )
    from .common_imports import CADQUERY_AVAILABLE
except ImportError:
    # Fallback for direct execution
    from export_patterns import (
        safe_export_with_cleanup, validate_export_result, create_test_export_object
    )
    from common_imports import CADQUERY_AVAILABLE


class TestExportPatterns(unittest.TestCase):
    """Tests for common export patterns."""

    def test_validate_export_result_success(self):
        """Test export result validation with valid data."""
        valid_data = b"valid export data with sufficient content"
        is_valid, error = validate_export_result(valid_data, 10)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_export_result_too_small(self):
        """Test export result validation with too small data."""
        small_data = b"small"
        is_valid, error = validate_export_result(small_data, 10)
        self.assertFalse(is_valid)
        self.assertIn("too small", error)

    def test_validate_export_result_wrong_type(self):
        """Test export result validation with wrong data type."""
        wrong_data = "not bytes"
        is_valid, error = validate_export_result(wrong_data)
        self.assertFalse(is_valid)
        self.assertIn("not bytes", error)

    def test_validate_export_result_empty_bytes(self):
        """Test export result validation with empty bytes."""
        empty_data = b""
        is_valid, error = validate_export_result(empty_data, 5)
        self.assertFalse(is_valid)
        self.assertIn("too small", error)

    def test_validate_export_result_exact_minimum(self):
        """Test export result validation with exactly minimum size."""
        exact_data = b"12345"  # Exactly 5 bytes
        is_valid, error = validate_export_result(exact_data, 5)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_create_test_export_object_returns_appropriate_value(self):
        """Test creation of test export object returns appropriate value."""
        obj = create_test_export_object()
        if CADQUERY_AVAILABLE:
            self.assertIsNotNone(obj)
        else:
            self.assertIsNone(obj)

    def test_safe_export_with_cleanup_with_failing_function(self):
        """Test safe export with cleanup when export function fails."""
        def failing_export(*args, **kwargs):
            raise ValueError("Export failed")
        
        success, result = safe_export_with_cleanup(failing_export)
        self.assertFalse(success)
        self.assertIsInstance(result, str)
        self.assertIn("Export failed", result)

    def test_safe_export_with_cleanup_with_none_function(self):
        """Test safe export with cleanup when function is None."""
        # This should handle the case gracefully
        success, result = safe_export_with_cleanup(None)
        self.assertFalse(success)
        self.assertIsInstance(result, str)

    def test_validate_export_result_with_various_sizes(self):
        """Test validation with different minimum sizes."""
        data = b"test data of medium length"
        
        # Should pass with small minimum
        is_valid, _ = validate_export_result(data, 5)
        self.assertTrue(is_valid)
        
        # Should fail with large minimum
        is_valid, _ = validate_export_result(data, 100)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
