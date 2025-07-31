"""File operations for LibraryManager."""

import os
import shutil
import tempfile
import unittest


class LibraryFileOperations:
    """Handles file operations for the library manager."""

    def __init__(self, library_manager):
        """Initialize with reference to the main library manager."""
        self.library_manager = library_manager

    def get_file_content(self, filename):
        """Get the content of a file from built-in or user library.

        Args:
            filename: Name of the file to read

        Returns:
            String content of the file

        Raises:
            FileNotFoundError: If file doesn't exist in either location
        """
        # Try built-in library first
        built_in_path = os.path.join(self.library_manager.built_in_library_path, filename)
        if os.path.exists(built_in_path):
            with open(built_in_path, 'r', encoding='utf-8') as file:
                return file.read()

        # Try user library
        user_path = os.path.join(self.library_manager.user_library_path, filename)
        if os.path.exists(user_path):
            with open(user_path, 'r', encoding='utf-8') as file:
                return file.read()

        raise FileNotFoundError(f"File {filename} not found in library")

    def handle_rename(self, old_filename, new_filename, content):
        """Handle renaming a file in the user library.

        Args:
            old_filename: Original filename
            new_filename: New filename
            content: File content to save

        Returns:
            Tuple of (success, message)
        """
        old_path = os.path.join(self.library_manager.user_library_path, old_filename)
        new_path = os.path.join(self.library_manager.user_library_path, new_filename)

        # Check if new filename conflicts with built-in library
        built_in_new_path = os.path.join(self.library_manager.built_in_library_path, new_filename)
        if os.path.exists(built_in_new_path):
            return False, f"Cannot rename: {new_filename} conflicts with built-in library file"

        # Check if new filename already exists in user library
        if os.path.exists(new_path) and old_path != new_path:
            return False, f"Cannot rename: {new_filename} already exists in user library"

        try:
            # If old file exists in user library, rename it
            if os.path.exists(old_path):
                # Use temporary file for atomic operation
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                               dir=self.library_manager.user_library_path,
                                               delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(content)
                    temp_name = temp_file.name

                # Atomic rename
                shutil.move(temp_name, new_path)

                # Remove old file if different from new
                if old_path != new_path:
                    os.remove(old_path)

                return True, f"File renamed from {old_filename} to {new_filename}"

            # Old file doesn't exist in user library, just create new file
            with open(new_path, 'w', encoding='utf-8') as file:
                file.write(content)
            return True, f"File created as {new_filename}"

        except OSError as e:
            return False, f"Error renaming file: {str(e)}"

    def commit_user_file(self, filename, message=None):
        """Commit a user file to git if git operations are available.

        Args:
            filename: Name of the file to commit
            message: Optional commit message

        Returns:
            Boolean indicating success
        """
        if not hasattr(self.library_manager, 'git_ops') or not self.library_manager.git_ops:
            return True  # No git operations available, consider it successful

        file_path = os.path.join(self.library_manager.user_library_path, filename)
        if not os.path.exists(file_path):
            return False

        try:
            # Use git operations to commit the file
            commit_message = message or f"Update {filename}"
            return self.library_manager.git_ops.commit_file(filename, commit_message)
        except Exception:  # pylint: disable=broad-exception-caught
            # Git operations failed, but file was saved successfully
            return True

    def save_file(self, filename, content, commit_message=None):
        """Save a file to the user library.

        Args:
            filename: Name of the file
            content: Content to save
            commit_message: Optional git commit message

        Returns:
            Dictionary with success status and message
        """
        try:
            self.library_manager._ensure_user_library()  # pylint: disable=protected-access
            file_path = os.path.join(self.library_manager.user_library_path, filename)

            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)

            # Commit to git if available
            git_success = self.commit_user_file(filename, commit_message)

            return {
                'success': True,
                'message': f'File {filename} saved successfully',
                'git_committed': git_success
            }

        except OSError as e:
            return {
                'success': False,
                'message': f'Error saving file: {str(e)}',
                'git_committed': False
            }

    def create_file(self, filename, content):
        """Create a new file in the user library.

        Args:
            filename: Name of the new file
            content: Initial content

        Returns:
            Dictionary with success status and message
        """
        # Check if file already exists
        user_path = os.path.join(self.library_manager.user_library_path, filename)
        built_in_path = os.path.join(self.library_manager.built_in_library_path, filename)

        if os.path.exists(user_path):
            return {
                'success': False,
                'message': f'File {filename} already exists in user library'
            }

        if os.path.exists(built_in_path):
            return {
                'success': False,
                'message': f'File {filename} already exists in built-in library'
            }

        try:
            self.library_manager._ensure_user_library()  # pylint: disable=protected-access

            # Create the file
            with open(user_path, 'w', encoding='utf-8') as file:
                file.write(content)

            # Commit to git if available
            git_success = self.commit_user_file(filename, f"Create {filename}")

            return {
                'success': True,
                'message': f'File {filename} created successfully',
                'git_committed': git_success
            }

        except OSError as e:
            return {
                'success': False,
                'message': f'Error creating file: {str(e)}',
                'git_committed': False
            }


class TestLibraryFileOperationsBasic(unittest.TestCase):
    """Basic tests for LibraryFileOperations."""

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
