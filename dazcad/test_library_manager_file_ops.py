"""
Basic tests for LibraryFileOperations module.
"""

import os
import tempfile
import unittest

try:
    from .library_manager_file_ops import LibraryFileOperations
    from .library_manager import LibraryManager
except ImportError:
    # Fallback for direct execution
    from library_manager_file_ops import LibraryFileOperations
    from library_manager import LibraryManager


class TestLibraryFileOperationsBasic(unittest.TestCase):
    """Basic tests for LibraryFileOperations."""

    def test_library_file_operations_creation(self):
        """Test that LibraryFileOperations can be created."""
        # Create a real library manager with temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            built_in_path = os.path.join(temp_dir, "built_in")
            user_path = os.path.join(temp_dir, "user")
            os.makedirs(built_in_path, exist_ok=True)
            os.makedirs(user_path, exist_ok=True)

            library_manager = LibraryManager(
                built_in_library_path=built_in_path,
                user_library_path=user_path
            )

            file_ops = library_manager.file_ops
            self.assertIsInstance(file_ops, LibraryFileOperations)
            self.assertEqual(file_ops.library_manager, library_manager)

    def test_get_file_content_with_missing_file(self):
        """Test getting content of a file that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            built_in_path = os.path.join(temp_dir, "built_in")
            user_path = os.path.join(temp_dir, "user")
            os.makedirs(built_in_path, exist_ok=True)
            os.makedirs(user_path, exist_ok=True)

            library_manager = LibraryManager(
                built_in_library_path=built_in_path,
                user_library_path=user_path
            )

            file_ops = library_manager.file_ops

            # Test file not found
            with self.assertRaises(FileNotFoundError):
                file_ops.get_file_content("nonexistent.py")

    def test_save_and_get_file_content(self):
        """Test saving a file and then reading it back."""
        with tempfile.TemporaryDirectory() as temp_dir:
            built_in_path = os.path.join(temp_dir, "built_in")
            user_path = os.path.join(temp_dir, "user")
            os.makedirs(built_in_path, exist_ok=True)
            os.makedirs(user_path, exist_ok=True)

            library_manager = LibraryManager(
                built_in_library_path=built_in_path,
                user_library_path=user_path
            )

            file_ops = library_manager.file_ops

            # Save a test file
            test_content = "# Test file content\\nprint('hello world')"
            result = file_ops.save_file("test.py", test_content)
            self.assertTrue(result['success'])

            # Read it back
            retrieved_content = file_ops.get_file_content("test.py")
            self.assertEqual(retrieved_content, test_content)
