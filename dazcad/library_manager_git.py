"""Git operations for LibraryManager."""

import subprocess
import unittest
from pathlib import Path
from typing import List, Dict, Tuple

# Import LLM functionality with fallback for direct execution
try:
    from .llm_chat import generate_git_commit_message
except ImportError:
    # Fallback for direct execution
    from llm_chat import generate_git_commit_message


class GitOperations:
    """Handles git operations for the library manager."""

    def __init__(self, library_path: Path):
        """Initialize git operations with library path.
        
        Args:
            library_path: Path to the library directory
        """
        self.library_path = library_path

    def ensure_git_initialized(self):
        """Ensure git repository is initialized in the library directory."""
        git_dir = self.library_path / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=self.library_path,
                    capture_output=True,
                    check=True
                )
                print(f"Initialized git repository in {self.library_path}")

                # Create initial commit
                gitignore_path = self.library_path / ".gitignore"
                gitignore_path.write_text("*.pyc\n__pycache__/\n.DS_Store\n")

                subprocess.run(
                    ["git", "add", ".gitignore"],
                    cwd=self.library_path,
                    capture_output=True,
                    check=True
                )

                subprocess.run(
                    ["git", "commit", "-m", "Initial commit with .gitignore"],
                    cwd=self.library_path,
                    capture_output=True,
                    check=True
                )

            except subprocess.CalledProcessError as e:
                print(f"Warning: Could not initialize git repository: {e}")

    def git_add_and_commit(self, filename: str, action: str, 
                          content: str) -> Tuple[bool, str]:
        """Add file to git and commit with generated message.
        
        Args:
            filename: Name of the file to add/commit
            action: Description of the action (for commit message)
            content: File content (for commit message generation)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Add file to git
            subprocess.run(
                ["git", "add", filename],
                cwd=self.library_path,
                capture_output=True,
                check=True
            )

            # Generate commit message using LLM
            commit_message = generate_git_commit_message(action, content)

            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.library_path,
                capture_output=True,
                check=True
            )

            return True, f"Committed: {commit_message}"

        except subprocess.CalledProcessError as e:
            return False, f"Git error: {e.stderr.decode() if e.stderr else str(e)}"

    def git_move_file(self, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Move/rename file using git.
        
        Args:
            old_name: Current filename
            new_name: New filename
            
        Returns:
            Tuple of (success, message)
        """
        try:
            subprocess.run(
                ["git", "mv", old_name, new_name],
                cwd=self.library_path,
                capture_output=True,
                check=True
            )
            return True, f"Renamed {old_name} to {new_name}"

        except subprocess.CalledProcessError as e:
            return False, f"Git rename error: {e.stderr.decode() if e.stderr else str(e)}"

    def get_file_history(self, filename: str) -> List[Dict[str, str]]:
        """Get git history for a specific file.
        
        Args:
            filename: Name of the file to get history for
            
        Returns:
            List of commit info dictionaries
        """
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H|%ai|%s", "--", filename],
                cwd=self.library_path,
                capture_output=True,
                text=True,
                check=True
            )

            history = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        history.append({
                            "hash": parts[0][:8],  # Short hash
                            "date": parts[1],
                            "message": parts[2]
                        })

            return history

        except subprocess.CalledProcessError:
            return []


class TestGitOperations(unittest.TestCase):
    """Unit tests for GitOperations."""

    def test_git_operations_creation(self):
        """Test that GitOperations can be created."""
        import tempfile  # pylint: disable=import-outside-toplevel
        temp_dir = Path(tempfile.mkdtemp())
        git_ops = GitOperations(temp_dir)
        self.assertIsNotNone(git_ops)
        self.assertEqual(git_ops.library_path, temp_dir)

    def test_git_methods_exist(self):
        """Test that required methods exist."""
        import tempfile  # pylint: disable=import-outside-toplevel
        temp_dir = Path(tempfile.mkdtemp())
        git_ops = GitOperations(temp_dir)
        
        self.assertTrue(hasattr(git_ops, 'ensure_git_initialized'))
        self.assertTrue(hasattr(git_ops, 'git_add_and_commit'))
        self.assertTrue(hasattr(git_ops, 'git_move_file'))
        self.assertTrue(hasattr(git_ops, 'get_file_history'))
