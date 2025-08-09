"""Common export patterns and utilities to reduce code duplication."""

import os
import tempfile
from typing import Tuple, Any

try:
    from .common_imports import CADQUERY_AVAILABLE
except ImportError:
    from common_imports import CADQUERY_AVAILABLE

if CADQUERY_AVAILABLE:
    import cadquery as cq  # pylint: disable=invalid-name
else:
    cq = None  # pylint: disable=invalid-name


def safe_export_with_cleanup(export_func, *args, **kwargs) -> Tuple[bool, Any]:
    """Safely execute export function with automatic cleanup.

    Args:
        export_func: Export function to execute
        *args: Arguments to pass to export function
        **kwargs: Keyword arguments to pass to export function

    Returns:
        Tuple of (success, result_or_error)
    """
    tmp_filename = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
            tmp_filename = tmp_file.name

        # Execute export function
        result = export_func(*args, tmp_filename=tmp_filename, **kwargs)

        # Read result if export was successful
        if os.path.exists(tmp_filename):
            with open(tmp_filename, 'rb') as f:
                data = f.read()
            return True, data

        return True, result

    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, str(e)
    finally:
        # Clean up temporary file
        if tmp_filename and os.path.exists(tmp_filename):
            try:
                os.unlink(tmp_filename)
            except OSError:
                pass  # Ignore cleanup errors


def validate_export_result(result: bytes, min_size: int = 10) -> Tuple[bool, str]:
    """Validate export result has meaningful content.

    Args:
        result: Export result data
        min_size: Minimum expected size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(result, bytes):
        return False, f"Export result is not bytes, got {type(result)}"

    if len(result) < min_size:
        return False, f"Export result too small: {len(result)} bytes (minimum {min_size})"

    return True, ""


def create_test_export_object():
    """Create a simple test object for export testing.

    Returns:
        CadQuery object or None if CadQuery not available
    """
    if not CADQUERY_AVAILABLE or cq is None:
        return None

    try:
        return cq.Workplane("XY").box(10, 10, 10)
    except Exception:  # pylint: disable=broad-exception-caught
        return None
