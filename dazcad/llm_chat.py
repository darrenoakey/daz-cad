"""LLM chat functionality for DazCAD - provides AI assistance for code generation."""

import unittest

# Import core functionality
try:
    from .llm_core import (
        CodeResponse, get_llm, generate_git_commit_message,
        improve_code_with_llm, get_current_model
    )
except ImportError:
    # Fallback for direct execution
    from llm_core import (
        CodeResponse, get_llm, generate_git_commit_message,
        improve_code_with_llm, get_current_model
    )

# Re-export all functions for backward compatibility
__all__ = [
    'CodeResponse', 'get_llm', 'generate_git_commit_message',
    'improve_code_with_llm', 'get_current_model'
]


class TestLlmChatModule(unittest.TestCase):
    """Tests for LLM chat module."""

    def test_module_imports(self):
        """Test that all expected functions are imported."""
        for func_name in __all__:
            self.assertTrue(globals().get(func_name) is not None,
                          f"Function {func_name} not imported")

    def test_basic_functionality(self):
        """Test basic module functionality."""
        # Test model management
        current_model = get_current_model()
        self.assertIsInstance(current_model, str)
        self.assertGreater(len(current_model), 0)

        # Test LLM client retrieval
        llm = get_llm()
        self.assertIsNotNone(llm, "LLM client should always be available")

    def test_code_response_model(self):
        """Test CodeResponse model functionality."""
        response = CodeResponse(
            success=True,
            code="test_code = 'example'",
            explanation="This is test code"
        )
        self.assertTrue(response.success)
        self.assertEqual(response.code, "test_code = 'example'")
        self.assertEqual(response.explanation, "This is test code")
