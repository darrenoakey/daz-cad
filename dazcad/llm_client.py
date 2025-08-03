"""LLM client management and initialization."""

import traceback
import unittest
from dazllm import Llm  # Import directly here for testing

# Note: Assuming pydantic is available for chat_structured tests
from pydantic import BaseModel

# Global LLM model name and client
_LLM_MODEL_NAME = "ollama:mistral-small"
_LLM_CLIENT = None


def get_llm():
    """Get the LLM client, initializing if necessary."""
    global _LLM_CLIENT  # pylint: disable=global-statement
    if _LLM_CLIENT is None:
        try:
            _LLM_CLIENT = Llm.model_named(_LLM_MODEL_NAME)
            print(f"LLM initialized successfully with model: {_LLM_MODEL_NAME}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error initializing LLM: {e}")
            traceback.print_exc()
            raise RuntimeError(f"Failed to initialize LLM: {e}") from e
    return _LLM_CLIENT


def get_current_model() -> str:
    """Get the current LLM model name."""
    return _LLM_MODEL_NAME


class TestLlmClient(unittest.TestCase):
    """Tests for LLM client management."""

    def test_client_functions_exist(self):
        """Test that client functions exist."""
        self.assertTrue(callable(get_llm))
        self.assertTrue(callable(get_current_model))

    def test_llm_always_available(self):
        """Test that LLM is always available."""
        llm = get_llm()
        self.assertIsNotNone(llm, "LLM should always be available")

    def test_current_model_retrieval(self):
        """Test getting current model name."""
        model_name = get_current_model()
        self.assertIsInstance(model_name, str)
        self.assertGreater(len(model_name), 0)

    def test_llm_has_correct_dazllm_methods(self):
        """Test that retrieved LLM has correct dazllm API methods."""
        llm = get_llm()
        self.assertIsNotNone(llm, "LLM client should be initialized")
        # Verify LLM has the correct methods from dazllm API
        self.assertTrue(
            hasattr(llm, "chat"),
            "LLM client should have 'chat' method from dazllm API",
        )
        self.assertTrue(
            hasattr(llm, "chat_structured"),
            "LLM client should have 'chat_structured' method from dazllm API",
        )
        # Ensure it doesn't have incorrect method names
        self.assertFalse(hasattr(llm, "invoke"), "LLM should not have 'invoke' method")

    def test_dazllm_import_and_usage(self):
        """Test that dazllm can be imported and used correctly."""
        # No skip; let it fail if import or attributes are missing
        import dazllm  # pylint: disable=import-outside-toplevel

        # Test that dazllm has the expected API
        self.assertTrue(hasattr(dazllm, "Llm"), "dazllm should have Llm class")
        # Test that Llm class has correct methods
        if hasattr(dazllm, "Llm"):
            llm_class = dazllm.Llm
            # Check if chat method exists in class
            self.assertTrue(
                hasattr(llm_class, "chat"),
                "dazllm.Llm class should have 'chat' method",
            )
            self.assertTrue(
                hasattr(llm_class, "chat_structured"),
                "dazllm.Llm class should have 'chat_structured' method",
            )

    def test_chat_method(self):
        """Test the chat method of the LLM client."""
        llm = get_llm()
        self.assertIsNotNone(llm, "LLM client should be initialized")
        # Test with a simple string prompt
        result = llm.chat("Hello, this is a test prompt. Respond with 'test response'.")
        self.assertIsInstance(result, str, "chat should return a string")
        self.assertGreater(len(result), 0, "chat response should not be empty")
        # Test with a conversation array
        conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "This is a test"},
        ]
        result_conv = llm.chat(conversation)
        self.assertIsInstance(
            result_conv, str, "chat with conversation should return a string"
        )
        self.assertGreater(len(result_conv), 0, "chat response should not be empty")

    def test_chat_structured_method(self):
        """Test the chat_structured method of the LLM client."""
        llm = get_llm()
        self.assertIsNotNone(llm, "LLM client should be initialized")

        class TestResponse(BaseModel):
            """Test Pydantic model for structured output."""

            message: str
            number: int

        prompt = "Respond with a message 'hello' and number 42."
        result = llm.chat_structured(prompt, TestResponse)
        self.assertIsInstance(
            result,
            TestResponse,
            "chat_structured should return an instance of the given class",
        )
        self.assertTrue(
            hasattr(result, "message"), "Result should have 'message' attribute"
        )
        self.assertTrue(
            hasattr(result, "number"), "Result should have 'number' attribute"
        )
        self.assertIsInstance(result.message, str, "'message' should be a string")
        self.assertIsInstance(result.number, int, "'number' should be an integer")
