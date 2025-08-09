"""CadQuery file execution functionality."""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional

def _import_cadquery(module_name: str = "cadquery"):
    """Import CadQuery and return (cq_module, available_flag)."""
    try:
        if module_name == "cadquery":
            import cadquery as cq
            return cq, True
        else:
            # For testing - try to import a non-existent module
            __import__(module_name)
            return None, True
    except ImportError:
        return None, False

# Initialize CadQuery availability
cq, CADQUERY_AVAILABLE = _import_cadquery()


def execute_cadquery_file(file_path: Path, cq_module: Optional[Any] = None) -> Tuple[bool, Dict[str, Any], str]:
    """Execute a CadQuery file and capture results.

    Args:
        file_path: Path to the CadQuery Python file
        cq_module: Optional CadQuery module (for testing)

    Returns:
        Tuple of (success, result_dict, error_message)
        result_dict contains 'shown_objects' and 'globals'
    """
    # Use provided module or default
    cq_to_use = cq_module if cq_module is not None else cq

    # Read the file content
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            code = file.read()
    except IOError as e:
        return False, {}, f"Failed to read file: {e}"

    # Set up execution environment
    shown_objects = []

    def show_object(obj, name=None, color=None):
        """Capture objects to be displayed."""
        shown_objects.append({
            'object': obj,
            'name': name or f'Object_{len(shown_objects)}',
            'color': color
        })
        return obj

    # Execute the code
    exec_globals = {
        '__name__': '__main__',
        'show_object': show_object,
        'cq': cq_to_use
    }

    try:
        exec(code, exec_globals)  # pylint: disable=exec-used
        return True, {'shown_objects': shown_objects, 'globals': exec_globals}, ""
    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, {}, f"Execution error: {type(e).__name__}: {e}"
