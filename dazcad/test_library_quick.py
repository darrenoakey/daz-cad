#!/usr/bin/env python3
"""Quick library test - run this directly to debug library loading."""

import os
import sys
import traceback
import unittest

# Add the current directory to the path so we can import dazcad modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import modules with fallbacks
try:
    from library_manager import LibraryManager
    LIBRARY_MANAGER_AVAILABLE = True
except ImportError:
    LibraryManager = None
    LIBRARY_MANAGER_AVAILABLE = False

try:
    from dazcad.colored_logging import log_debug, log_success, log_error
    COLORED_LOGGING_AVAILABLE = True
except ImportError:
    log_debug = log_success = log_error = None
    COLORED_LOGGING_AVAILABLE = False

print("=== Quick Library Test ===")
print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path}")
print()


def test_library_paths():
    """Test library path resolution."""
    print("1. Testing library path resolution:")

    # Expected library path
    expected_library = os.path.join(current_dir, "library")
    print(f"   Expected library path: {expected_library}")
    print(f"   Library path exists: {os.path.exists(expected_library)}")

    if os.path.exists(expected_library):
        try:
            contents = os.listdir(expected_library)
            print(f"   Library contents: {contents}")

            py_files = [f for f in contents if f.endswith('.py') and not f.startswith('__')]
            print(f"   Python files: {py_files}")
            print(f"   Found {len(py_files)} Python library files")

            return len(py_files) > 0
        except (OSError, PermissionError) as e:
            print(f"   ERROR listing library: {e}")
            return False
    else:
        print("   ERROR: Library directory does not exist!")
        return False


def test_library_manager_import():
    """Test importing and using LibraryManager."""
    print("\\n2. Testing LibraryManager import:")

    if not LIBRARY_MANAGER_AVAILABLE:
        print("   ERROR: LibraryManager not available")
        return False

    try:
        print("   ✓ LibraryManager imported successfully")

        # Try to create it with explicit path
        library_path = os.path.join(current_dir, "library")
        manager = LibraryManager(built_in_library_path=library_path)
        print("   ✓ LibraryManager created successfully")

        # Try to list files
        files = manager.list_files()
        print(f"   Files found: {files}")

        built_in_count = len(files.get('built_in', []))
        user_count = len(files.get('user', []))
        print(f"   Built-in files: {built_in_count}")
        print(f"   User files: {user_count}")

        if built_in_count > 0:
            print("   ✓ Library loading working correctly!")
            return True

        print("   ✗ No built-in files found - library loading broken")
        return False

    except (OSError, AttributeError, TypeError, KeyError) as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        return False


def test_colored_logging():
    """Test colored logging import."""
    print("\\n3. Testing colored logging:")

    if not COLORED_LOGGING_AVAILABLE:
        print("   ERROR: Colored logging not available")
        return False

    try:
        print("   ✓ Colored logging imported successfully")

        log_debug("TEST", "This is a debug message")
        log_success("TEST", "This is a success message")
        log_error("TEST", "This is an error message")

        return True
    except (AttributeError, TypeError) as e:
        print(f"   ERROR: {e}")
        return False


def main():
    """Run all tests."""
    print("Starting library diagnostics...\\n")

    path_ok = test_library_paths()
    manager_ok = test_library_manager_import()
    logging_ok = test_colored_logging()

    print("\\n=== SUMMARY ===")
    print(f"Library paths: {'✓' if path_ok else '✗'}")
    print(f"LibraryManager: {'✓' if manager_ok else '✗'}")
    print(f"Colored logging: {'✓' if logging_ok else '✗'}")

    if all([path_ok, manager_ok, logging_ok]):
        print("\\n✓ All tests passed! Library should work in server.")
        return True

    print("\\n✗ Some tests failed - library loading is broken")
    return False


class TestLibraryQuick(unittest.TestCase):
    """Quick library tests."""

    def test_library_paths(self):
        """Test library path resolution."""
        self.assertTrue(test_library_paths())

    def test_library_manager(self):
        """Test library manager functionality."""
        self.assertTrue(test_library_manager_import())


if __name__ == "__main__":
    SUCCESS = main()
    sys.exit(0 if SUCCESS else 1)
