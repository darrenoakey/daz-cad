"""Core LibraryManager class for DazCAD library management."""

import unittest
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Import git operations with fallback for direct execution
try:
    from .library_manager_git import GitOperations
except ImportError:
    # Fallback for direct execution
    from library_manager_git import GitOperations


class LibraryManager:
    """Manages example library and user library with git integration."""

    def __init__(self, built_in_library_path: str = "library",
                 user_library_path: str = None):
        """Initialize library manager with paths to libraries.

        Args:
            built_in_library_path: Path to built-in examples (relative to app)
            user_library_path: Path to user library (defaults to ~/dazcad/library)
        """
        self.built_in_library_path = Path(built_in_library_path)

        if user_library_path is None:
            user_library_path = Path.home() / "dazcad" / "library"
        self.user_library_path = Path(user_library_path)

        # Initialize git operations for user library
        self.git_ops = GitOperations(self.user_library_path)

        # Ensure user library exists and is initialized with git
        self._ensure_user_library()

    def _ensure_user_library(self):
        """Ensure user library directory exists and has git initialized."""
        # Create directory if it doesn't exist
        self.user_library_path.mkdir(parents=True, exist_ok=True)

        # Initialize git if not already initialized
        self.git_ops.ensure_git_initialized()

    def list_files(self) -> Dict[str, List[Dict[str, str]]]:
        """List all library files from both built-in and user libraries.

        Returns:
            Dictionary with 'builtin' and 'user' keys containing file lists
        """
        result = {
            "builtin": [],
            "user": []
        }

        # List built-in library files
        if self.built_in_library_path.exists():
            for file_path in sorted(self.built_in_library_path.glob("*.py")):
                result["builtin"].append({
                    "name": file_path.stem,
                    "path": str(file_path),
                    "type": "builtin"
                })

        # List user library files
        if self.user_library_path.exists():
            for file_path in sorted(self.user_library_path.glob("*.py")):
                result["user"].append({
                    "name": file_path.stem,
                    "path": str(file_path),
                    "type": "user"
                })

        return result

    def get_file_content(self, name: str, file_type: str = "user") -> Optional[str]:
        """Get content of a library file.

        Args:
            name: File name (without .py extension)
            file_type: Either 'user' or 'builtin'

        Returns:
            File content or None if not found
        """
        if file_type == "builtin":
            file_path = self.built_in_library_path / f"{name}.py"
        else:
            file_path = self.user_library_path / f"{name}.py"

        if file_path.exists():
            return file_path.read_text()
        return None

    def save_file(self, name: str, content: str, old_name: Optional[str] = None,
                  file_type: str = "user") -> Tuple[bool, str]:
        """Save a library file and commit to git if in user library.

        Args:
            name: File name (without .py extension)
            content: File content
            old_name: Previous name if renaming
            file_type: Either 'user' or 'builtin'

        Returns:
            Tuple of (success, message)
        """
        # Determine file path based on type
        if file_type == "builtin":
            file_path = self.built_in_library_path / f"{name}.py"
        else:
            file_path = self.user_library_path / f"{name}.py"

        try:
            # Handle rename if old_name provided
            if old_name and old_name != name:
                old_path = file_path.parent / f"{old_name}.py"
                if old_path.exists():
                    if file_type == "user":
                        # Use git mv for user files
                        success, msg = self.git_ops.git_move_file(f"{old_name}.py", f"{name}.py")
                        if not success:
                            return False, msg
                    else:
                        # Just rename for built-in files
                        old_path.rename(file_path)

            # Write the file
            file_path.write_text(content)

            # For user files, commit to git
            if file_type == "user":
                if old_name and old_name != name:
                    action = f"Renamed {old_name} to {name} and updated"
                else:
                    action = f"Updated {name}"

                success, msg = self.git_ops.git_add_and_commit(f"{name}.py", action, content)
                if success:
                    return True, f"Saved and {msg}"
                else:
                    return False, msg

            return True, f"Saved {name}.py"

        except Exception as e:  # pylint: disable=broad-exception-caught
            return False, f"Error saving file: {str(e)}"

    def create_file(self, name: str, content: str = "") -> Tuple[bool, str]:
        """Create a new file in the user library.

        Args:
            name: File name (without .py extension)
            content: Initial content (defaults to 3D printing ready template)

        Returns:
            Tuple of (success, message)
        """
        file_path = self.user_library_path / f"{name}.py"

        if file_path.exists():
            return False, f"File {name}.py already exists"

        # Use 3D printing ready template if no content provided
        if not content:
            content = '''"""3D Printable CadQuery model"""

import cadquery as cq

# Create your model here - positioned to sit on the build plate (z=0)
result = cq.Workplane("XY").workplane(offset=5).box(20, 20, 10)

# Show the result
show_object(result, name="MyModel")
'''

        return self.save_file(name, content)

    def get_git_history(self, name: str) -> List[Dict[str, str]]:
        """Get git history for a file in the user library.

        Args:
            name: File name (without .py extension)

        Returns:
            List of commit info dictionaries
        """
        return self.git_ops.get_file_history(f"{name}.py")


class TestLibraryManagerCore(unittest.TestCase):
    """Basic tests for LibraryManager core functionality."""

    def test_library_manager_creation(self):
        """Test that LibraryManager can be created."""
        import tempfile  # pylint: disable=import-outside-toplevel
        temp_dir = tempfile.mkdtemp()
        manager = LibraryManager(
            built_in_library_path=temp_dir,
            user_library_path=temp_dir
        )
        self.assertIsNotNone(manager)
        self.assertTrue(hasattr(manager, 'list_files'))

    def test_file_path_setup(self):
        """Test that file paths are properly set up."""
        manager = LibraryManager()
        self.assertIsNotNone(manager.built_in_library_path)
        self.assertIsNotNone(manager.user_library_path)
        self.assertIsNotNone(manager.git_ops)
