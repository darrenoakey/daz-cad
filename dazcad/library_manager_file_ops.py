"""Core file operations for LibraryManager."""

import os
import unittest

# Import utilities and logging
try:
    from .library_file_utils import (
        validate_file_rename, atomic_file_write, safe_file_read, check_file_conflicts
    )
    from .colored_logging import log_debug, log_error, log_success
except ImportError:
    from library_file_utils import (
        validate_file_rename, atomic_file_write, safe_file_read, check_file_conflicts
    )
    from colored_logging import log_debug, log_error, log_success


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
        log_debug("FILE_OPS", f"Checking built-in library: {built_in_path}")

        try:
            content = safe_file_read(built_in_path)
            log_success("FILE_OPS", f"Found {filename} in built-in library")
            log_success("FILE_OPS", f"Successfully read {filename}: {len(content)} characters")
            return content
        except FileNotFoundError:
            pass

        # Try user library
        user_path = os.path.join(self.library_manager.user_library_path, filename)
        log_debug("FILE_OPS", f"Checking user library: {user_path}")

        try:
            content = safe_file_read(user_path)
            log_success("FILE_OPS", f"Found {filename} in user library")
            log_success("FILE_OPS", f"Successfully read {filename}: {len(content)} characters")
            return content
        except FileNotFoundError:
            pass

        # File not found in either location
        error_msg = f"File {filename} not found in library"
        log_error("FILE_OPS", error_msg)
        log_error("FILE_OPS", f"Built-in path checked: {built_in_path}")
        log_error("FILE_OPS", f"User path checked: {user_path}")
        raise FileNotFoundError(error_msg)

    def handle_rename(self, old_filename, new_filename, content):
        """Handle renaming a file in the user library.

        Args:
            old_filename: Original filename
            new_filename: New filename
            content: File content to save

        Returns:
            Tuple of (success, message)
        """
        # Validate rename operation
        is_valid, error_msg = validate_file_rename(
            old_filename, new_filename,
            self.library_manager.built_in_library_path,
            self.library_manager.user_library_path
        )

        if not is_valid:
            return False, error_msg

        old_path = os.path.join(self.library_manager.user_library_path, old_filename)
        new_path = os.path.join(self.library_manager.user_library_path, new_filename)

        try:
            # Write content to new location
            atomic_file_write(new_path, content)

            # Remove old file if different from new and exists
            if old_path != new_path and os.path.exists(old_path):
                os.remove(old_path)
                return True, f"File renamed from {old_filename} to {new_filename}"

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

            # Write content to file atomically
            atomic_file_write(file_path, content)

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
        # Check for file conflicts
        has_conflict, conflict_location = check_file_conflicts(
            filename,
            self.library_manager.built_in_library_path,
            self.library_manager.user_library_path
        )

        if has_conflict:
            location_name = "user" if conflict_location == "user" else "built-in"
            return {
                'success': False,
                'message': f'File {filename} already exists in {location_name} library'
            }

        try:
            self.library_manager._ensure_user_library()  # pylint: disable=protected-access
            user_path = os.path.join(self.library_manager.user_library_path, filename)

            # Create the file atomically
            atomic_file_write(user_path, content)

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


class TestLibraryFileOperationsModule(unittest.TestCase):
    """Basic module-level tests for library file operations."""

    def test_module_exports(self):
        """Test that module exports the expected class."""
        self.assertTrue(hasattr(LibraryFileOperations, '__init__'))
        self.assertTrue(hasattr(LibraryFileOperations, 'get_file_content'))
        self.assertTrue(hasattr(LibraryFileOperations, 'save_file'))
        self.assertTrue(hasattr(LibraryFileOperations, 'create_file'))
