"""Unit tests for GitOperations."""

import unittest
from pathlib import Path

try:
    from .library_manager_git import GitOperations
except ImportError:
    # Fallback for direct execution
    from library_manager_git import GitOperations


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


if __name__ == '__main__':
    unittest.main()
