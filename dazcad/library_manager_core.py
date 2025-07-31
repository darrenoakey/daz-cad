"""Core library management functionality."""

import os
import tempfile
import unittest

try:
    from .library_manager_git import GitOperations
    from .library_manager_file_ops import LibraryFileOperations
except ImportError:
    # Fallback for direct execution
    from library_manager_git import GitOperations
    from library_manager_file_ops import LibraryFileOperations


class LibraryManager:
    """Manages CAD library files with git integration."""

    def __init__(self, built_in_library_path=None, user_library_path=None):
        """Initialize the library manager.

        Args:
            built_in_library_path: Path to built-in library files
            user_library_path: Path to user library files (default: ~/.dazcad/library)
        """
        # Set up paths
        if built_in_library_path:
            self.built_in_library_path = built_in_library_path
        else:
            # Default to library subdirectory of this file's directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.built_in_library_path = os.path.join(current_dir, 'library')

        if user_library_path:
            self.user_library_path = user_library_path
        else:
            # Default to ~/.dazcad/library
            home_dir = os.path.expanduser('~')
            self.user_library_path = os.path.join(home_dir, '.dazcad', 'library')

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
        built_in_files = []
        user_files = []

        # List built-in files
        if os.path.exists(self.built_in_library_path):
            try:
                for filename in os.listdir(self.built_in_library_path):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        built_in_files.append(filename)
            except OSError:
                # Directory not accessible
                pass

        # List user files
        if os.path.exists(self.user_library_path):
            try:
                for filename in os.listdir(self.user_library_path):
                    if (filename.endswith('.py') and
                        not filename.startswith('__') and
                        not filename.startswith('.')):
                        user_files.append(filename)
            except OSError:
                # Directory not accessible
                pass

        return {
            'built_in': sorted(built_in_files),
            'user': sorted(user_files)
        }

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

    def save_file(self, filename, content, commit_message=None):
        """Save a file to the user library.

        Args:
            filename: Name of the file
            content: Content to save
            commit_message: Optional git commit message

        Returns:
            Dictionary with success status and message
        """
        # Handle filename changes
        original_filename = filename
        if '/' in filename or '\\' in filename:
            # Extract just the filename part
            filename = os.path.basename(filename)

        # Check if this is a rename operation
        if original_filename != filename and original_filename.endswith('.py'):
            success, message = self.file_ops.handle_rename(original_filename, filename, content)
            if not success:
                return {'success': False, 'message': message}

        return self.file_ops.save_file(filename, content, commit_message)

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
