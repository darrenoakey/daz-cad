"""Comprehensive tests for LibraryManager file operations."""

import os
import shutil
import tempfile
import unittest

from .library_manager import LibraryManager


class TestLibraryFileOperations(unittest.TestCase):
    """Comprehensive tests for LibraryManager file operations."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp()
        self.built_in_dir = os.path.join(self.test_dir, "built_in")
        self.user_dir = os.path.join(self.test_dir, "user")
        os.makedirs(self.built_in_dir)
        os.makedirs(self.user_dir)

        # Create a real library manager instance with test directories
        self.library_manager = LibraryManager(
            built_in_library_path=self.built_in_dir,
            user_library_path=self.user_dir
        )

    def tearDown(self):
        """Clean up test environment."""
        # Remove test directories
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_handle_rename_validation(self):
        """Test rename validation logic."""
        # Test renaming non-existent file (should create new file)
        success, message = self.library_manager._handle_rename("old.py", "new.py", "content")
        self.assertTrue(success)
        self.assertIn("created as", message)

        # Verify file was created
        new_path = os.path.join(self.user_dir, "new.py")
        self.assertTrue(os.path.exists(new_path))

        # Test renaming to existing file name
        success, message = self.library_manager._handle_rename("another.py", "new.py", "different content")
        self.assertFalse(success)
        self.assertIn("already exists", message)

    def test_get_file_content_from_built_in(self):
        """Test getting file content from built-in library."""
        # Create a test file in built-in directory
        test_content = "# Test file\\nprint('Hello')"
        test_file = os.path.join(self.built_in_dir, "test.py")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # Get the content
        content = self.library_manager.get_file_content("test.py")
        self.assertEqual(content, test_content)

    def test_get_file_content_from_user(self):
        """Test getting file content from user library."""
        # Create a test file in user directory
        test_content = "# User file\\nprint('User')"
        test_file = os.path.join(self.user_dir, "user_test.py")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # Get the content
        content = self.library_manager.get_file_content("user_test.py")
        self.assertEqual(content, test_content)

    def test_get_file_content_not_found(self):
        """Test getting file content that doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            self.library_manager.get_file_content("nonexistent.py")

    def test_save_file(self):
        """Test saving a file to user library."""
        test_content = "# Saved file\\nprint('Saved')"
        success, message = self.library_manager.save_file("saved.py", test_content)

        self.assertTrue(success)
        self.assertIn('saved successfully', message)

        # Verify file was created
        saved_path = os.path.join(self.user_dir, "saved.py")
        self.assertTrue(os.path.exists(saved_path))

        # Verify content
        with open(saved_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), test_content)

    def test_create_file(self):
        """Test creating a new file in user library."""
        test_content = "# New file\\nprint('New')"
        result = self.library_manager.create_file("new.py", test_content)

        self.assertTrue(result['success'])
        self.assertIn('created successfully', result['message'])

        # Verify file was created
        new_path = os.path.join(self.user_dir, "new.py")
        self.assertTrue(os.path.exists(new_path))

    def test_create_file_already_exists(self):
        """Test creating a file that already exists."""
        # Create a file first
        existing_file = os.path.join(self.user_dir, "existing.py")
        with open(existing_file, 'w', encoding='utf-8') as f:
            f.write("existing")

        # Try to create it again
        result = self.library_manager.create_file("existing.py", "new content")

        self.assertFalse(result['success'])
        self.assertIn('already exists', result['message'])

    def test_handle_rename_with_built_in_conflict(self):
        """Test renaming to a name that conflicts with built-in library."""
        # Create a file in built-in library
        built_in_file = os.path.join(self.built_in_dir, "protected.py")
        with open(built_in_file, 'w', encoding='utf-8') as f:
            f.write("# Built-in file")

        # Try to rename to that name
        success, message = self.library_manager._handle_rename("user.py", "protected.py", "user content")

        self.assertFalse(success)
        self.assertIn('conflicts with built-in library', message)

    def test_commit_user_file_without_git(self):
        """Test committing when git operations are not available."""
        # Create a file
        test_file = os.path.join(self.user_dir, "test.py")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test")

        # Try to commit (should succeed even without git)
        result = self.library_manager._commit_user_file("test.py", "test", "test")
        self.assertTrue(result)

    def test_library_manager_integration(self):
        """Test integration with LibraryManager."""
        # Test that paths are correctly set
        self.assertEqual(self.library_manager.built_in_library_path, self.built_in_dir)
        self.assertEqual(self.library_manager.user_library_path, self.user_dir)

    def test_list_files(self):
        """Test file listing functionality."""
        # Create test files
        built_in_file = os.path.join(self.built_in_dir, "builtin_test.py")
        user_file = os.path.join(self.user_dir, "user_test.py")
        
        with open(built_in_file, 'w', encoding='utf-8') as f:
            f.write("# Built-in test")
        with open(user_file, 'w', encoding='utf-8') as f:
            f.write("# User test")

        # Test file listing
        files = self.library_manager.list_files()
        
        self.assertIn('built_in', files)
        self.assertIn('user', files)
        self.assertIn('builtin_test.py', files['built_in'])
        self.assertIn('user_test.py', files['user'])


if __name__ == '__main__':
    unittest.main()
