"""Basic tests for LibraryManager file operations."""

import unittest
import tempfile
import os

# Import test utilities
try:
    from .library_manager import LibraryManager
except ImportError:
    from library_manager import LibraryManager


class TestLibraryFileOperationsBasic(unittest.TestCase):
    """Basic tests for LibraryManager file operations."""

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

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_library_manager_creation(self):
        """Test that LibraryManager can be created."""
        self.assertIsInstance(self.library_manager, LibraryManager)
        self.assertEqual(self.library_manager.built_in_library_path, self.built_in_path)
        self.assertEqual(self.library_manager.user_library_path, self.user_path)

    def test_save_and_get_file_content(self):
        """Test saving a file and then reading it back."""
        filename = "test.py"
        content = "# Test content\\nprint('Hello, World!')"
        
        # Save the file
        success, message = self.library_manager.save_file(filename, content)
        self.assertTrue(success)
        self.assertIn('saved successfully', message)
        
        # Read it back
        retrieved_content = self.library_manager.get_file_content(filename)
        self.assertEqual(retrieved_content, content)

    def test_get_file_content_with_missing_file(self):
        """Test getting content of a file that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.library_manager.get_file_content("nonexistent.py")

    def test_create_file(self):
        """Test creating a new file."""
        filename = "new_file.py"
        content = "# New file content\\nprint('New file!')"
        
        # Create the file
        result = self.library_manager.create_file(filename, content)
        self.assertTrue(result['success'])
        self.assertIn('created successfully', result['message'])
        
        # Verify it exists and has correct content
        retrieved_content = self.library_manager.get_file_content(filename)
        self.assertEqual(retrieved_content, content)

    def test_list_files(self):
        """Test listing files in both directories."""
        # Create test files
        built_in_file = os.path.join(self.built_in_path, "builtin.py")
        with open(built_in_file, 'w', encoding='utf-8') as f:
            f.write("# Built-in file")
            
        # Create user file through library manager
        self.library_manager.save_file("user.py", "# User file")
        
        # List files
        files = self.library_manager.list_files()
        
        self.assertIn('built_in', files)
        self.assertIn('user', files)
        self.assertIn('builtin.py', files['built_in'])
        self.assertIn('user.py', files['user'])


if __name__ == '__main__':
    unittest.main()
