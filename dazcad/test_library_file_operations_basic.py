"""Basic tests for LibraryFileOperations class."""

import unittest
import tempfile
import os

# Import test utilities
try:
    from .library_manager_file_ops import LibraryFileOperations
    from .library_manager_core import LibraryManager
except ImportError:
    from library_manager_file_ops import LibraryFileOperations
    from library_manager_core import LibraryManager


class TestLibraryFileOperationsBasic(unittest.TestCase):
    """Basic tests for LibraryFileOperations."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.built_in_path = os.path.join(self.temp_dir, "built_in")
        self.user_path = os.path.join(self.temp_dir, "user")
        
        os.makedirs(self.built_in_path, exist_ok=True)
        os.makedirs(self.user_path, exist_ok=True)
        
        # Create test library manager
        self.library_manager = LibraryManager(
            built_in_library_path=self.built_in_path,
            user_library_path=self.user_path
        )
        
        # Create file operations instance
        self.file_ops = LibraryFileOperations(self.library_manager)

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_library_file_operations_creation(self):
        """Test that LibraryFileOperations can be created."""
        self.assertIsInstance(self.file_ops, LibraryFileOperations)
        self.assertEqual(self.file_ops.library_manager, self.library_manager)

    def test_save_and_get_file_content(self):
        """Test saving a file and then reading it back."""
        filename = "test.py"
        content = "# Test content\nprint('Hello, World!')"
        
        # Save the file
        result = self.file_ops.save_file(filename, content)
        self.assertTrue(result['success'])
        
        # Read it back
        retrieved_content = self.file_ops.get_file_content(filename)
        self.assertEqual(retrieved_content, content)

    def test_get_file_content_with_missing_file(self):
        """Test getting content of a file that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.file_ops.get_file_content("nonexistent.py")
