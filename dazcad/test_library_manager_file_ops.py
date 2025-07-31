"""
Tests for LibraryFileOperations module.
"""

import unittest

try:
    from .library_manager_file_ops import LibraryFileOperations
except ImportError:
    # Fallback for direct execution
    from library_manager_file_ops import LibraryFileOperations


class TestLibraryFileOperations(unittest.TestCase):
    """Tests for LibraryFileOperations."""

    def test_library_file_operations_creation(self):
        """Test that LibraryFileOperations can be created."""
        # Create a mock library manager
        class MockLibraryManager:  # pylint: disable=too-few-public-methods
            """Mock library manager for testing."""
            def __init__(self):
                self.built_in_library_path = "/tmp/built_in"
                self.user_library_path = "/tmp/user"

        mock_manager = MockLibraryManager()
        file_ops = LibraryFileOperations(mock_manager)
        self.assertIsInstance(file_ops, LibraryFileOperations)
        self.assertEqual(file_ops.library_manager, mock_manager)

    def test_handle_rename_validation(self):
        """Test rename validation logic."""
        class MockLibraryManager:  # pylint: disable=too-few-public-methods
            """Mock library manager for testing."""
            def __init__(self):
                self.built_in_library_path = "/tmp/built_in"
                self.user_library_path = "/tmp/user"

        mock_manager = MockLibraryManager()
        file_ops = LibraryFileOperations(mock_manager)

        # Test with non-existent paths (should not raise exception)
        success, message = file_ops.handle_rename("old.py", "new.py", "content")
        self.assertIsInstance(success, bool)
        self.assertIsInstance(message, str)
