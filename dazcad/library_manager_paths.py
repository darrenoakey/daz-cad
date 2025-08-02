"""Path management for library manager."""

import os
import unittest

try:
    from .colored_logging import log_library_operation, log_debug, log_error
except ImportError:
    # Fallback for direct execution
    from colored_logging import log_library_operation, log_debug, log_error


class LibraryPathManager:  # pylint: disable=too-few-public-methods
    """Manages paths for built-in and user library directories."""

    def __init__(self, built_in_library_path=None, user_library_path=None):
        """Initialize path manager.

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

        log_library_operation("INIT", f"Built-in path: {self.built_in_library_path}")
        log_library_operation("INIT", f"User path: {self.user_library_path}")
        log_library_operation("INIT",
                              f"Built-in exists: {os.path.exists(self.built_in_library_path)}")
        log_library_operation("INIT",
                              f"User exists: {os.path.exists(self.user_library_path)}")

        # List contents of built-in directory for debugging
        if os.path.exists(self.built_in_library_path):
            try:
                contents = os.listdir(self.built_in_library_path)
                log_debug("LIBRARY", f"Built-in directory contents: {contents}")
            except OSError as e:
                log_error("LIBRARY", f"Cannot list built-in directory: {e}")

    def list_files(self):
        """List all available library files.

        Returns:
            Dictionary with 'built_in' and 'user' lists of filenames
        """
        log_library_operation("LIST_FILES", "Starting file listing")
        built_in_files = []
        user_files = []

        # List built-in files
        log_debug("LIBRARY", f"Checking built-in path: {self.built_in_library_path}")
        if os.path.exists(self.built_in_library_path):
            try:
                all_files = os.listdir(self.built_in_library_path)
                log_debug("LIBRARY", f"All files in built-in directory: {all_files}")

                for filename in all_files:
                    log_debug("LIBRARY", f"Checking file: {filename}")
                    if filename.endswith('.py') and not filename.startswith('__'):
                        built_in_files.append(filename)
                        log_debug("LIBRARY", f"Added built-in file: {filename}")
                    else:
                        log_debug("LIBRARY",
                                  f"Skipped file: {filename} (not .py or starts with __)")

            except OSError as e:
                # Directory not accessible
                log_error("LIBRARY", f"Cannot access built-in library: {e}")
        else:
            log_error("LIBRARY",
                      f"Built-in library path does not exist: {self.built_in_library_path}")

        # List user files
        log_debug("LIBRARY", f"Checking user path: {self.user_library_path}")
        if os.path.exists(self.user_library_path):
            try:
                all_files = os.listdir(self.user_library_path)
                log_debug("LIBRARY", f"All files in user directory: {all_files}")

                for filename in all_files:
                    if (filename.endswith('.py') and
                        not filename.startswith('__') and
                        not filename.startswith('.')):
                        user_files.append(filename)
                        log_debug("LIBRARY", f"Added user file: {filename}")

            except OSError as e:
                # Directory not accessible
                log_error("LIBRARY", f"Cannot access user library: {e}")

        result = {
            'built_in': sorted(built_in_files),
            'user': sorted(user_files)
        }

        log_library_operation("LIST_FILES",
                              f"Found {len(built_in_files)} built-in, {len(user_files)} user files")
        log_debug("LIBRARY", f"Final result: {result}")

        return result


class TestLibraryPathManager(unittest.TestCase):
    """Tests for LibraryPathManager."""

    def test_path_manager_creation(self):
        """Test that LibraryPathManager can be created."""
        manager = LibraryPathManager()
        self.assertIsInstance(manager, LibraryPathManager)
        self.assertIsNotNone(manager.built_in_library_path)
        self.assertIsNotNone(manager.user_library_path)

    def test_list_files_method_exists(self):
        """Test that list_files method exists and returns proper structure."""
        manager = LibraryPathManager()
        files = manager.list_files()
        self.assertIsInstance(files, dict)
        self.assertIn('built_in', files)
        self.assertIn('user', files)
        self.assertIsInstance(files['built_in'], list)
        self.assertIsInstance(files['user'], list)
