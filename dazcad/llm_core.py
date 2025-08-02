"""Core LLM functionality for DazCAD."""

import unittest
from typing import Optional

from pydantic import BaseModel

# Import LLM functionality from specialized modules
try:
    from .llm_client import (
        set_llm_model, get_llm, is_llm_available, get_current_model
    )
    from .llm_code_improvement import improve_code_with_llm
    from .llm_git_utils import generate_git_commit_message
except ImportError:
    # Fallback for direct execution
    from llm_client import (
        set_llm_model, get_llm, is_llm_available, get_current_model
    )
    from llm_code_improvement import improve_code_with_llm
    from llm_git_utils import generate_git_commit_message


class CodeResponse(BaseModel):
    """Response model for code generation from LLM."""
    success: bool
    code: str
    explanation: str
    error: Optional[str] = None


class TestLlmCore(unittest.TestCase):
    """Basic tests for LLM core functionality."""

    def test_model_setting(self):
        """Test setting and getting model name."""
        original_model = get_current_model()
        set_llm_model("test:model")
        self.assertEqual(get_current_model(), "test:model")
        # Restore original
        set_llm_model(original_model)

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

    def test_all_functions_available(self):
        """Test that all expected functions are available."""
        self.assertTrue(callable(set_llm_model))
        self.assertTrue(callable(get_llm))
        self.assertTrue(callable(is_llm_available))
        self.assertTrue(callable(get_current_model))
        self.assertTrue(callable(improve_code_with_llm))
        self.assertTrue(callable(generate_git_commit_message))
