"""Common validation patterns to reduce code duplication."""

import unittest
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


def check_common_validation_assertions(test_case, result: Dict[str, Any]):
    """Perform common validation assertions on a result.

    Args:
        test_case: unittest.TestCase instance
        result: Validation result to check
    """
    # Check result structure
    test_case.assertIsInstance(result, dict)
    test_case.assertIn('success', result)
    test_case.assertIn('file', result)
    test_case.assertIn('execution_error', result)
    test_case.assertIn('objects', result)
    test_case.assertIn('summary', result)

    # Check summary structure
    summary = result['summary']
    test_case.assertIn('total_objects', summary)
    test_case.assertIn('valid_objects', summary)
    test_case.assertIn('total_export_tests', summary)
    test_case.assertIn('successful_exports', summary)


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


class TestValidationPatterns(unittest.TestCase):
    """Tests for common validation patterns."""

    def test_create_validation_result_template(self):
        """Test validation result template creation."""
        template = create_validation_result_template()

        is_valid, error = validate_result_structure(template)
        self.assertTrue(is_valid, f"Template validation failed: {error}")

    def test_validate_result_structure_valid(self):
        """Test result structure validation with valid data."""
        valid_result = create_validation_result_template()
        is_valid, error = validate_result_structure(valid_result)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_result_structure_invalid(self):
        """Test result structure validation with invalid data."""
        invalid_result = {"incomplete": "data"}
        is_valid, error = validate_result_structure(invalid_result)
        self.assertFalse(is_valid)
        self.assertIn("Missing required key", error)

    def test_check_common_validation_assertions(self):
        """Test common validation assertions."""
        result = create_validation_result_template()

        # Should not raise any assertions
        try:
            check_common_validation_assertions(self, result)
        except AssertionError:
            self.fail("Common validation assertions failed on valid template")

    def test_create_test_object_info(self):
        """Test test object info creation."""
        obj_info = create_test_object_info("TestObj", "assembly")

        self.assertEqual(obj_info['name'], "TestObj")
        self.assertEqual(obj_info['type'], "assembly")
        self.assertIsNone(obj_info['object'])
        
        # Verify it has the expected structure
        self.assertIsInstance(obj_info, dict)
        self.assertIn('object', obj_info)
        self.assertIn('name', obj_info)
        self.assertIn('type', obj_info)

    def test_validation_pattern_functions_exist(self):
        """Test that all expected validation pattern functions exist."""
        self.assertTrue(callable(create_validation_result_template))
        self.assertTrue(callable(validate_result_structure))
        self.assertTrue(callable(check_common_validation_assertions))
        self.assertTrue(callable(create_test_object_info))
