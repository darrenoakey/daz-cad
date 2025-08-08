"""Tests for LLM core functionality."""

import unittest

try:
    from .llm_core import CodeResponse
    from .llm_client import get_llm, get_current_model
    from .llm_code_improvement import improve_code_with_llm
    from .llm_git_utils import generate_git_commit_message
except ImportError:
    # Fallback for direct execution
    from llm_core import CodeResponse
    from llm_client import get_llm, get_current_model
    from llm_code_improvement import improve_code_with_llm
    from llm_git_utils import generate_git_commit_message


class TestLlmCore(unittest.TestCase):
    """Basic tests for LLM core functionality."""

    def test_code_response_model(self):
        """Test CodeResponse model structure."""
        response = CodeResponse(
            success=True,
            code="test code",
            explanation="test explanation"
        )
        self.assertTrue(response.success)
        self.assertEqual(response.code, "test code")
        self.assertEqual(response.explanation, "test explanation")
        self.assertIsNone(response.error)

    def test_code_response_model_with_error(self):
        """Test CodeResponse model structure with error."""
        response = CodeResponse(
            success=False,
            code="",
            explanation="test failed",
            error="Test error message"
        )
        self.assertFalse(response.success)
        self.assertEqual(response.code, "")
        self.assertEqual(response.explanation, "test failed")
        self.assertEqual(response.error, "Test error message")

    def test_all_functions_available(self):
        """Test that all expected functions are available."""
        self.assertTrue(callable(get_llm))
        self.assertTrue(callable(get_current_model))
        self.assertTrue(callable(improve_code_with_llm))
        self.assertTrue(callable(generate_git_commit_message))

    def test_llm_client_functionality(self):
        """Test that LLM client functions work correctly."""
        # Test model name retrieval
        model_name = get_current_model()
        self.assertIsInstance(model_name, str)
        self.assertGreater(len(model_name), 0)

        # Test LLM client retrieval
        llm = get_llm()
        self.assertIsNotNone(llm, "LLM client should always be available")

    def test_imports_available(self):
        """Test that all imports are available and functional."""
        # Test that we can import the modules successfully
        self.assertIsNotNone(get_llm)
        self.assertIsNotNone(get_current_model)
        self.assertIsNotNone(improve_code_with_llm)
        self.assertIsNotNone(generate_git_commit_message)
        self.assertIsNotNone(CodeResponse)


if __name__ == '__main__':
    unittest.main()
