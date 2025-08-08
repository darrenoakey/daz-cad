"""Common validation patterns to reduce code duplication."""

from typing import Dict, Any, Tuple


def create_validation_result_template() -> Dict[str, Any]:
    """Create a standard validation result template.

    Returns:
        Dictionary with standard validation result structure
    """
    return {
        'success': True,
        'file': '',
        'execution_error': '',
        'objects': [],
        'summary': {
            'total_objects': 0,
            'valid_objects': 0,
            'total_export_tests': 0,
            'successful_exports': 0
        }
    }


def validate_result_structure(result: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate that a result dictionary has the expected structure.

    Args:
        result: Result dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_keys = ['success', 'file', 'execution_error', 'objects', 'summary']

    if not isinstance(result, dict):
        return False, f"Result is not a dictionary, got {type(result)}"

    for key in required_keys:
        if key not in result:
            return False, f"Missing required key: {key}"

    # Validate summary structure
    summary = result.get('summary', {})
    if not isinstance(summary, dict):
        return False, "Summary is not a dictionary"

    summary_keys = ['total_objects', 'valid_objects', 'total_export_tests', 'successful_exports']
    for key in summary_keys:
        if key not in summary:
            return False, f"Missing summary key: {key}"

    return True, ""


def create_test_object_info(name: str = "TestObject", obj_type: str = "workplane"):
    """Create a test object info dictionary for validation testing.

    Args:
        name: Object name
        obj_type: Object type

    Returns:
        Test object info dictionary with real structure but None object
    """
    return {
        'object': None,  # Real structure but no actual object for testing
        'name': name,
        'type': obj_type
    }
