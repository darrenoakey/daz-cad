"""Utility functions for library file operations."""

import os
import tempfile
import shutil


def validate_file_rename(old_filename, new_filename, built_in_path, user_path):
    """Validate if a file can be renamed.

    Args:
        old_filename: Original filename
        new_filename: New filename
        built_in_path: Path to built-in library
        user_path: Path to user library

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if new filename conflicts with built-in library
    built_in_new_path = os.path.join(built_in_path, new_filename)
    if os.path.exists(built_in_new_path):
        return False, f"Cannot rename: {new_filename} conflicts with built-in library file"

    # Check if new filename already exists in user library
    old_path = os.path.join(user_path, old_filename)
    new_path = os.path.join(user_path, new_filename)
    if os.path.exists(new_path) and old_path != new_path:
        return False, f"Cannot rename: {new_filename} already exists in user library"

    return True, ""


def atomic_file_write(file_path, content):
    """Write content to file atomically using temporary file.

    Args:
        file_path: Destination file path
        content: Content to write

    Returns:
        Boolean indicating success

    Raises:
        OSError: If file operation fails
    """
    directory = os.path.dirname(file_path)

    # Use temporary file for atomic operation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                   dir=directory,
                                   delete=False, encoding='utf-8') as temp_file:
        temp_file.write(content)
        temp_name = temp_file.name

    # Atomic rename
    shutil.move(temp_name, file_path)
    return True


def safe_file_read(file_path):
    """Safely read file content with proper encoding.

    Args:
        file_path: Path to file to read

    Returns:
        String content of the file

    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file can't be read
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def check_file_conflicts(filename, built_in_path, user_path):
    """Check if a filename conflicts with existing files.

    Args:
        filename: Name of the file to check
        built_in_path: Path to built-in library
        user_path: Path to user library

    Returns:
        Tuple of (has_conflict, conflict_location)
        conflict_location is 'built_in', 'user', or None
    """
    user_file_path = os.path.join(user_path, filename)
    built_in_file_path = os.path.join(built_in_path, filename)

    if os.path.exists(user_file_path):
        return True, 'user'

    if os.path.exists(built_in_file_path):
        return True, 'built_in'

    return False, None
