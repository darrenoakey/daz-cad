"""Core LLM functionality for DazCAD."""

import traceback
import unittest
from typing import Optional, Callable

from pydantic import BaseModel

# Global LLM model name
_LLM_MODEL_NAME = "ollama:mixtral:8x7b"
_LLM_CLIENT = None


class CodeResponse(BaseModel):
    """Response model for code generation from LLM."""
    success: bool
    code: str
    explanation: str
    error: Optional[str] = None


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


def generate_git_commit_message(action: str, code_content: str) -> str:
    """Generate a descriptive git commit message using LLM.

    Args:
        action: The action being performed (e.g., "Updated example")
        code_content: The code content to analyze

    Returns:
        Generated commit message or fallback message
    """
    llm = get_llm()
    if not llm:
        return f"{action} - Auto-commit"

    try:
        # Create a prompt for generating commit message
        prompt = f"""Analyze this CadQuery code and generate a concise git commit message.

Action: {action}

Code:
{code_content[:1000]}  # Limit code length

Generate a commit message that:
1. Starts with a verb (e.g., "Add", "Update", "Fix", "Create")
2. Is under 50 characters
3. Describes what the code creates or changes
4. Uses present tense

Examples:
- "Add parametric gear with 20 teeth"
- "Update bracket with mounting holes"
- "Create spiral vase model"
- "Fix bearing dimensions"

Commit message:"""

        response = llm.invoke(prompt)

        if hasattr(response, 'content'):
            commit_msg = response.content.strip()
        else:
            commit_msg = str(response).strip()

        # Clean up the response - remove quotes and extra text
        if commit_msg.startswith('"') and commit_msg.endswith('"'):
            commit_msg = commit_msg[1:-1]

        # Take just the first line and limit length
        commit_msg = commit_msg.split('\n')[0][:50]

        return commit_msg if commit_msg else f"{action} - Auto-commit"

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error generating commit message: {e}")
        return f"{action} - Auto-commit"


def improve_code_with_llm(user_message: str, current_code: str,
                         code_runner: Callable[[str], dict]) -> dict:
    """Use LLM to improve CadQuery code based on user message.

    Args:
        user_message: User's request for code modification
        current_code: Current CadQuery code
        code_runner: Function to test if code runs successfully

    Returns:
        Dictionary with success, response, code, and run_result
    """
    llm = get_llm()
    if not llm:
        return {
            "success": False,
            "response": "LLM not available. Please check your dazllm installation.",
            "code": current_code
        }

    try:
        # Create a detailed prompt for code improvement
        prompt = f"""You are an expert CadQuery assistant. \
Help modify this CadQuery code based on the user's request.

Current code:
```python
{current_code}
```

User request: {user_message}

Important guidelines:
1. All models must sit on or above z=0 plane (3D printing compatible)
2. Use workplane(offset=height/2) to position objects on the build plate
3. Keep imports and show_object() calls
4. Provide working, complete code
5. Use descriptive variable names
6. Add helpful comments

Respond with ONLY the complete Python code, no explanations or markdown:"""

        response = llm.invoke(prompt)

        if hasattr(response, 'content'):
            new_code = response.content.strip()
        else:
            new_code = str(response).strip()

        # Clean up the response - remove markdown code blocks if present
        if new_code.startswith('```python'):
            new_code = new_code[9:]
        if new_code.startswith('```'):
            new_code = new_code[3:]
        if new_code.endswith('```'):
            new_code = new_code[:-3]

        new_code = new_code.strip()

        # Test the new code
        test_result = code_runner(new_code)

        if test_result.get("success"):
            return {
                "success": True,
                "response": "I've updated your code based on your request. " \
                           "The changes have been applied and the model is ready!",
                "code": new_code,
                "run_result": test_result
            }

        # Code didn't work, return original with explanation
        error_msg = test_result.get('error', 'Unknown error')
        return {
            "success": False,
            "response": f"I generated new code but it has errors: {error_msg}. " \
                       "Keeping your original code.",
            "code": current_code,
            "error": test_result.get('error')
        }

    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "success": False,
            "response": f"Sorry, I encountered an error: {str(e)}",
            "code": current_code,
            "error": str(e)
        }


def is_llm_available() -> bool:
    """Check if LLM is available and working."""
    return get_llm() is not None


def get_current_model() -> str:
    """Get the current LLM model name."""
    return _LLM_MODEL_NAME


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
