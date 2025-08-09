"""Library manager for DazCAD - handles example libraries and user library with git integration."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .library_file_utils import (
    validate_file_rename, atomic_file_write, safe_file_read, check_file_conflicts
)
from .colored_logging import log_library_operation, log_debug, log_error, log_success

# Optional git support
try:
    from .library_manager_git import GitOperations
    GIT_AVAILABLE = True
except ImportError:
    GitOperations = None
    GIT_AVAILABLE = False


class LibraryManager:
    """Manages CAD library files with git integration."""

    def __init__(self, built_in_library_path: Optional[str] = None, 
                 user_library_path: Optional[str] = None):
        """Initialize the library manager.

        Args:
            built_in_library_path: Path to built-in library files
            user_library_path: Path to user library files (default: ~/.dazcad/library)
        """
        # Set up paths
        self.built_in_library_path = self._get_built_in_path(built_in_library_path)
        self.user_library_path = self._get_user_path(user_library_path)
        
        # Initialize git operations if available
        self.git_ops = None
        if GIT_AVAILABLE:
            try:
                self.git_ops = GitOperations(Path(self.user_library_path))
            except Exception:  # pylint: disable=broad-exception-caught
                # Git operations not available
                pass

        # Ensure user library exists
        self._ensure_user_library()

        # Log initialization
        log_library_operation("INIT", f"Built-in path: {self.built_in_library_path}")
        log_library_operation("INIT", f"User path: {self.user_library_path}")
        log_library_operation("INIT", f"Git available: {self.git_ops is not None}")

    def _get_built_in_path(self, path: Optional[str]) -> str:
        """Get built-in library path."""
        if path:
            return path
        # Default to library subdirectory of this file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'library')

    def _get_user_path(self, path: Optional[str]) -> str:
        """Get user library path."""
        if path:
            return path
        # Default to ~/.dazcad/library
        home_dir = os.path.expanduser('~')
        return os.path.join(home_dir, '.dazcad', 'library')

    def _ensure_user_library(self):
        """Ensure the user library directory exists and is initialized."""
        os.makedirs(self.user_library_path, exist_ok=True)

        # Initialize git repository if git operations are available
        if self.git_ops:
            try:
                self.git_ops.ensure_git_initialized()
            except Exception:  # pylint: disable=broad-exception-caught
                # Git initialization failed, continue without git
                self.git_ops = None

    def list_files(self) -> Dict[str, List[str]]:
        """List all available library files.

        Returns:
            Dictionary with 'built_in' and 'user' lists of filenames
        """
        log_library_operation("LIST_FILES", "Starting file listing")
        
        built_in_files = self._list_files_in_directory(self.built_in_library_path, "built-in")
        user_files = self._list_files_in_directory(self.user_library_path, "user")

        result = {
            'built_in': sorted(built_in_files),
            'user': sorted(user_files)
        }

        log_library_operation("LIST_FILES", 
                              f"Found {len(built_in_files)} built-in, {len(user_files)} user files")
        return result

    def _list_files_in_directory(self, directory_path: str, directory_name: str) -> List[str]:
        """List Python files in a directory."""
        files = []
        
        if not os.path.exists(directory_path):
            log_error("LIBRARY", f"{directory_name} library path does not exist: {directory_path}")
            return files

        try:
            all_files = os.listdir(directory_path)
            log_debug("LIBRARY", f"All files in {directory_name} directory: {all_files}")

            for filename in all_files:
                if (filename.endswith('.py') and 
                    not filename.startswith('__') and 
                    not filename.startswith('.')):
                    files.append(filename)
                    log_debug("LIBRARY", f"Added {directory_name} file: {filename}")

        except OSError as e:
            log_error("LIBRARY", f"Cannot access {directory_name} library: {e}")

        return files

    def get_file_content(self, filename: str) -> str:
        """Get the content of a file from built-in or user library.

        Args:
            filename: Name of the file to read

        Returns:
            String content of the file

        Raises:
            FileNotFoundError: If file doesn't exist in either location
        """
        # Try built-in library first
        built_in_path = os.path.join(self.built_in_library_path, filename)
        log_debug("FILE_OPS", f"Checking built-in library: {built_in_path}")

        try:
            content = safe_file_read(built_in_path)
            log_success("FILE_OPS", f"Found {filename} in built-in library")
            return content
        except FileNotFoundError:
            pass

        # Try user library
        user_path = os.path.join(self.user_library_path, filename)
        log_debug("FILE_OPS", f"Checking user library: {user_path}")

        try:
            content = safe_file_read(user_path)
            log_success("FILE_OPS", f"Found {filename} in user library")
            return content
        except FileNotFoundError:
            pass

        # File not found in either location
        error_msg = f"File {filename} not found in library"
        log_error("FILE_OPS", error_msg)
        raise FileNotFoundError(error_msg)

    def save_file(self, filename: str, content: str, file_type: str = 'user', 
                  options: Optional[Dict] = None) -> Tuple[bool, str]:
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

        # Check if this is a rename operation
        if old_name and old_name != filename and old_name.endswith('.py'):
            success, message = self._handle_rename(old_name, filename, content)
            if not success:
                return False, message

        # Handle regular save operation
        result = self._save_file_to_user_library(filename, content, commit_message)
        return result['success'], result['message']

    def _handle_rename(self, old_filename: str, new_filename: str, content: str) -> Tuple[bool, str]:
        """Handle renaming a file in the user library."""
        # Validate rename operation
        is_valid, error_msg = validate_file_rename(
            old_filename, new_filename,
            self.built_in_library_path,
            self.user_library_path
        )

        if not is_valid:
            return False, error_msg

        old_path = os.path.join(self.user_library_path, old_filename)
        new_path = os.path.join(self.user_library_path, new_filename)

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

    def _save_file_to_user_library(self, filename: str, content: str, 
                                   commit_message: Optional[str] = None) -> Dict:
        """Save a file to the user library."""
        try:
            self._ensure_user_library()
            file_path = os.path.join(self.user_library_path, filename)

            # Write content to file atomically
            atomic_file_write(file_path, content)

            # Commit to git if available
            git_success = self._commit_user_file(filename, content, commit_message)

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

    def create_file(self, filename: str, content: str) -> Dict:
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
            self.built_in_library_path,
            self.user_library_path
        )

        if has_conflict:
            location_name = "user" if conflict_location == "user" else "built-in"
            return {
                'success': False,
                'message': f'File {filename} already exists in {location_name} library'
            }

        try:
            self._ensure_user_library()
            user_path = os.path.join(self.user_library_path, filename)

            # Create the file atomically
            atomic_file_write(user_path, content)

            # Commit to git if available
            git_success = self._commit_user_file(filename, content, f"Create {filename}")

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

    def _commit_user_file(self, filename: str, content: str, message: Optional[str] = None) -> bool:
        """Commit a user file to git if git operations are available."""
        if not self.git_ops:
            return True  # No git operations available, consider it successful

        file_path = os.path.join(self.user_library_path, filename)
        if not os.path.exists(file_path):
            return False

        try:
            # Use git operations to commit the file
            action = message or f"Update {filename}"
            success, _ = self.git_ops.git_add_and_commit(filename, action, content)
            return success
        except Exception:  # pylint: disable=broad-exception-caught
            # Git operations failed, but file was saved successfully
            return True

    def get_git_history(self, filename: Optional[str] = None, max_entries: int = 10) -> List:
        """Get git history for a file or the entire repository.

        Args:
            filename: Optional filename to get history for
            max_entries: Maximum number of history entries to return

        Returns:
            List of history entries or empty list if git not available
        """
        if not self.git_ops or not filename:
            return []

        try:
            history = self.git_ops.get_file_history(filename)
            return history[:max_entries] if history else []
        except Exception:  # pylint: disable=broad-exception-caught
            return []


# Re-export for backward compatibility
__all__ = ['LibraryManager']
