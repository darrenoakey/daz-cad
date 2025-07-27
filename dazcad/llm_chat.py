"""LLM chat functionality for DazCAD - provides AI assistance for code generation."""

import unittest

# Import core functionality
try:
    from .llm_core import (
        CodeResponse, set_llm_model, get_llm, generate_git_commit_message,
        improve_code_with_llm, is_llm_available, get_current_model
    )
except ImportError:
    # Fallback for direct execution
    from llm_core import (
        CodeResponse, set_llm_model, get_llm, generate_git_commit_message,
        improve_code_with_llm, is_llm_available, get_current_model
    )

# Re-export all functions for backward compatibility
__all__ = [
    'CodeResponse', 'set_llm_model', 'get_llm', 'generate_git_commit_message',
    'improve_code_with_llm', 'is_llm_available', 'get_current_model'
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
        original_model = get_current_model()
        self.assertIsInstance(original_model, str)

        # Test availability check
        available = is_llm_available()
        self.assertIsInstance(available, bool)
