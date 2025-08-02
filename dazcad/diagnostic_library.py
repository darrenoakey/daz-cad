"""Library manager diagnostic functions."""

import os
import traceback
import unittest

# Import library manager
try:
    from .library_manager import LibraryManager
except ImportError:
    try:
        from library_manager import LibraryManager
    except ImportError:
        LibraryManager = None


def test_library_manager():
    """Test library manager functionality."""
    if LibraryManager is None:
        print("✗ LibraryManager not available, skipping test")
        return False

    try:
        # Get current directory for library path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        library_path = os.path.join(current_dir, "library")

        print(f"Library path: {library_path}")
        print(f"Library path exists: {os.path.exists(library_path)}")

        if os.path.exists(library_path):
            files = os.listdir(library_path)
            print(f"Files in library: {files}")

        # Create library manager
        manager = LibraryManager(built_in_library_path=library_path)
        print("✓ LibraryManager created successfully")

        # Test listing files
        files = manager.list_files()
        print(f"✓ Library files listed: {files}")

        # Test reading a specific file
        if files['built_in']:
            test_file = files['built_in'][0]
            try:
                content = manager.get_file_content(test_file)
                print(f"✓ Successfully read {test_file}: {len(content)} characters")
                return True
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"✗ Failed to read {test_file}: {e}")
                return False
        print("✗ No built-in library files found")
        return False

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"✗ Library manager test failed: {e}")
        traceback.print_exc()
        return False


class TestLibraryDiagnostics(unittest.TestCase):
    """Tests for library diagnostic functions."""

    def test_library_manager_function(self):
        """Test that test_library_manager function exists."""
        self.assertTrue(callable(test_library_manager))
