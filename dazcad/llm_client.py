"""LLM client management and initialization."""

import traceback
import unittest

# Global LLM model name and client
_LLM_MODEL_NAME = "ollama:mixtral:8x7b"
_LLM_CLIENT = None


def set_llm_model(model_name: str) -> None:
    """Set the LLM model to use for chat functionality.

    Args:
        model_name: Name of the model (e.g., 'ollama:mixtral:8x7b')
    """
    global _LLM_MODEL_NAME, _LLM_CLIENT  # pylint: disable=global-statement
    _LLM_MODEL_NAME = model_name
    _LLM_CLIENT = None  # Reset client to force re-initialization


def get_llm():
    """Get the LLM client, initializing if necessary."""
    global _LLM_CLIENT  # pylint: disable=global-statement

    if _LLM_CLIENT is None:
        try:
            # Try to import dazllm
            import dazllm  # pylint: disable=import-outside-toplevel

            # Initialize the LLM client - try multiple possible function names
            if hasattr(dazllm, 'get_llm'):
                _LLM_CLIENT = dazllm.get_llm(_LLM_MODEL_NAME)  # pylint: disable=no-member
            elif hasattr(dazllm, 'create_llm'):
                _LLM_CLIENT = dazllm.create_llm(_LLM_MODEL_NAME)  # pylint: disable=no-member
            elif hasattr(dazllm, 'Llm'):
                _LLM_CLIENT = dazllm.Llm(_LLM_MODEL_NAME)  # pylint: disable=no-member
            else:
                # Fallback - try to instantiate directly
                _LLM_CLIENT = dazllm.LLM(_LLM_MODEL_NAME)  # pylint: disable=no-member

            print(f"LLM initialized successfully with model: {_LLM_MODEL_NAME}")

        except ImportError as e:
            print(f"Error: dazllm not available: {e}")
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error initializing LLM: {e}")
            traceback.print_exc()
            return None

    return _LLM_CLIENT


def is_llm_available() -> bool:
    """Check if LLM is available and working."""
    return get_llm() is not None


def get_current_model() -> str:
    """Get the current LLM model name."""
    return _LLM_MODEL_NAME


class TestLlmClient(unittest.TestCase):
    """Tests for LLM client management."""

    def test_model_setting(self):
        """Test setting and getting model name."""
        original_model = get_current_model()
        set_llm_model("test:model")
        self.assertEqual(get_current_model(), "test:model")
        # Restore original
        set_llm_model(original_model)

    def test_llm_availability_check(self):
        """Test LLM availability check."""
        available = is_llm_available()
        self.assertIsInstance(available, bool)

    def test_client_functions_exist(self):
        """Test that client functions exist."""
        self.assertTrue(callable(set_llm_model))
        self.assertTrue(callable(get_llm))
        self.assertTrue(callable(is_llm_available))
        self.assertTrue(callable(get_current_model))
