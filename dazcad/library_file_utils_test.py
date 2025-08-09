"""Tests for library file utility functions."""

import unittest

from .library_file_utils import (
    validate_file_rename, atomic_file_write, safe_file_read, check_file_conflicts
)


class TestLibraryFileUtils(unittest.TestCase):
    """Tests for library file utility functions."""

    def test_validate_file_rename_basic(self):
        """Test basic file rename validation."""
        # Test case where rename should be valid
        is_valid, error_msg = validate_file_rename("old.py", "new.py",
                                                  "/nonexistent", "/nonexistent")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")

    def test_check_file_conflicts_no_conflict(self):
        """Test file conflict checking with no conflicts."""
        has_conflict, location = check_file_conflicts("test.py",
                                                     "/nonexistent", "/nonexistent")
        self.assertFalse(has_conflict)
        self.assertIsNone(location)

    def test_safe_file_read_nonexistent(self):
        """Test safe file read with nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            safe_file_read("/nonexistent/file.py")

    def test_atomic_file_write_requires_valid_directory(self):
        """Test that atomic file write requires valid directory."""
        with self.assertRaises(OSError):
            atomic_file_write("/nonexistent/directory/file.py", "content")


if __name__ == '__main__':
    unittest.main()
