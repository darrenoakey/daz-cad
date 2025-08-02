"""Core library management functionality."""

import os
import tempfile
import unittest

try:
    from .library_manager_git import GitOperations
    from .library_manager_file_ops import LibraryFileOperations
    from .library_manager_paths import LibraryPathManager
except ImportError:
    # Fallback for direct execution
    from library_manager_git import GitOperations
    from library_manager_file_ops import LibraryFileOperations
    from library_manager_paths import LibraryPathManager


class LibraryManager:
    """Manages CAD library files with git integration."""

    def __init__(self, built_in_library_path=None, user_library_path=None):
        """Initialize the library manager.

        Args:
            built_in_library_path: Path to built-in library files
            user_library_path: Path to user library files (default: ~/.dazcad/library)
        """
        # Initialize path manager
        self.path_manager = LibraryPathManager(built_in_library_path, user_library_path)
        self.built_in_library_path = self.path_manager.built_in_library_path
        self.user_library_path = self.path_manager.user_library_path

        # Initialize git operations
        try:
            self.git_ops = GitOperations(self.user_library_path)
        except Exception:  # pylint: disable=broad-exception-caught
            # Git operations not available
            self.git_ops = None

        # Initialize file operations
        self.file_ops = LibraryFileOperations(self)

        # Ensure user library exists
        self._ensure_user_library()

    def _ensure_user_library(self):
        """Ensure the user library directory exists and is initialized."""
        os.makedirs(self.user_library_path, exist_ok=True)

        # Initialize git repository if git operations are available
        if self.git_ops and not os.path.exists(os.path.join(self.user_library_path, '.git')):
            try:
                self.git_ops.init_repository()
            except Exception:  # pylint: disable=broad-exception-caught
                # Git initialization failed, continue without git
                self.git_ops = None

    def list_files(self):
        """List all available library files.

        Returns:
            Dictionary with 'built_in' and 'user' lists of filenames
        """
        return self.path_manager.list_files()

    def get_file_content(self, filename):
        """Get the content of a file from built-in or user library.

        Args:
            filename: Name of the file to read

        Returns:
            String content of the file

        Raises:
            FileNotFoundError: If file doesn't exist in either location
        """
        return self.file_ops.get_file_content(filename)

    def save_file(self, filename, content, file_type='user', options=None):
        """Save a file to the user library.

        Args:
            filename: Name of the file
            content: Content to save
            file_type: Type of file ('user' or 'builtin') - currently unused, kept for compatibility
            options: Optional dict with 'old_name' and 'commit_message' keys

        Returns:
            Tuple of (success, message) for compatibility with calling code
        """
        # file_type is currently unused but kept for API compatibility
        _ = file_type

        # Extract options
        options = options or {}
        old_name = options.get('old_name')
        commit_message = options.get('commit_message')

        # Handle filename changes
        if '/' in filename or '\\' in filename:
            # Extract just the filename part
            filename = os.path.basename(filename)

        # Check if this is a rename operation (when old_name is provided and different)
        if old_name and old_name != filename and old_name.endswith('.py'):
            success, message = self.file_ops.handle_rename(old_name, filename, content)
            if not success:
                return False, message

        # Handle regular save operation
        result = self.file_ops.save_file(filename, content, commit_message)
        return result.get('success', False), result.get('message', 'Unknown error')

    def create_file(self, filename, content):
        """Create a new file in the user library.

        Args:
            filename: Name of the new file
            content: Initial content

        Returns:
            Dictionary with success status and message
        """
        return self.file_ops.create_file(filename, content)

    def get_git_history(self, filename=None, max_entries=10):
        """Get git history for a file or the entire repository.

        Args:
            filename: Optional filename to get history for
            max_entries: Maximum number of history entries to return

        Returns:
            List of history entries or empty list if git not available
        """
        if not self.git_ops:
            return []

        try:
            return self.git_ops.get_history(filename, max_entries)
        except Exception:  # pylint: disable=broad-exception-caught
            return []


class TestLibraryManagerCore(unittest.TestCase):
    """Tests for LibraryManager core functionality."""

    def test_library_manager_creation(self):
        """Test that LibraryManager can be created."""
        # Use temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            built_in_path = os.path.join(temp_dir, 'built_in')
            user_path = os.path.join(temp_dir, 'user')

            # Create directories
            os.makedirs(built_in_path, exist_ok=True)

            manager = LibraryManager(
                built_in_library_path=built_in_path,
                user_library_path=user_path
            )

            self.assertIsInstance(manager, LibraryManager)
            self.assertEqual(manager.built_in_library_path, built_in_path)
            self.assertEqual(manager.user_library_path, user_path)
            self.assertTrue(os.path.exists(user_path))

    def test_file_path_setup(self):
        """Test that file paths are properly set up."""
        # Test with default paths
        manager = LibraryManager()
        self.assertIsNotNone(manager.built_in_library_path)
        self.assertIsNotNone(manager.user_library_path)

        # Test list_files doesn't crash
        files = manager.list_files()
        self.assertIsInstance(files, dict)
        self.assertIn('built_in', files)
        self.assertIn('user', files)
        self.assertIsInstance(files['built_in'], list)
        self.assertIsInstance(files['user'], list)
