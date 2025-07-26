"""LLM chat functionality for DazCAD."""

import unittest
from typing import List
from pydantic import BaseModel

# Import dazllm for AI assistance
try:
    from dazllm import Llm
    DAZLLM_AVAILABLE = True
except ImportError:
    DAZLLM_AVAILABLE = False

# Global LLM instance - initialized once per program run
LLM_INSTANCE = None


class CodeResponse(BaseModel):
    """Structured response from LLM for code improvements"""
    explanation: str
    improved_code: str
    changes_made: List[str]


def get_llm():
    """Get or create the LLM instance"""
    global LLM_INSTANCE  # pylint: disable=global-statement
    if LLM_INSTANCE is None and DAZLLM_AVAILABLE:
        try:
            LLM_INSTANCE = Llm.model_named("ollama:llama3.2")  # LOCAL_LARGE
            print("LLM initialized successfully")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Failed to initialize LLM: {e}")
            LLM_INSTANCE = None
    return LLM_INSTANCE


def improve_code_with_llm(user_message, current_code, run_code_func):
    """
    Iteratively improve code using LLM

    Args:
        user_message: User's request
        current_code: Current CadQuery code
        run_code_func: Function to test code execution

    Returns:
        dict: Result with success status, response, new_code, objects, etc.
    """
    if not DAZLLM_AVAILABLE:
        return {
            "success": False,
            "error": "LLM not available",
            "response": "AI assistant is not available."
        }

    llm = get_llm()
    if not llm:
        return {
            "success": False,
            "error": "LLM not configured",
            "response": "AI assistant is not properly configured."
        }

    # Iterative improvement loop
    max_attempts = 10
    best_code = current_code
    last_error = None

    for attempt in range(max_attempts):
        print(f"Attempt {attempt + 1}/{max_attempts}")

        # Prepare conversation for LLM
        error_context = ""
        if last_error:
            error_context = f"Previous error encountered: {last_error}"

        conversation = f"""You are an expert CadQuery developer. User request: "{user_message}"

Current CadQuery code:
```python
{best_code}
```

{error_context}

Please provide improved code that:
1. Uses proper CadQuery syntax
2. Includes proper imports (import cadquery as cq)
3. Ends with show_object() to display the result
4. Is syntactically correct Python

Respond with structured format."""

        try:
            # Get structured response from LLM
            llm_response = llm.chat_structured(
                conversation=conversation,
                schema=CodeResponse,
                context_size=0
            )

            # Test the improved code
            test_result = run_code_func(llm_response.improved_code)

            if test_result["success"]:
                # Success! Return the improved code and result
                return {
                    "success": True,
                    "response": llm_response.explanation,
                    "new_code": llm_response.improved_code,
                    "objects": test_result["objects"],
                    "changes_made": llm_response.changes_made,
                    "attempts": attempt + 1
                }

            # Code didn't work, prepare for next iteration
            last_error = test_result["error"]
            print(f"Attempt {attempt + 1} failed: {last_error}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            last_error = f"LLM error: {str(e)}"
            print(f"LLM error in attempt {attempt + 1}: {e}")

    # All attempts failed
    error_msg = f"Failed after {max_attempts} attempts. Last error: {last_error}"
    response_msg = f"I tried {max_attempts} times but couldn't get it working. " \
                  f"Last error: {last_error}"
    return {
        "success": False,
        "error": error_msg,
        "response": response_msg
    }


def is_llm_available():
    """Check if LLM is available and configured"""
    return DAZLLM_AVAILABLE and get_llm() is not None


class LlmChatTests(unittest.TestCase):
    """Test LLM chat functionality"""

    def test_llm_availability(self):
        """Test LLM availability check"""
        # Should not raise an exception
        available = is_llm_available()
        self.assertIsInstance(available, bool)

    def test_code_response_model(self):
        """Test CodeResponse model"""
        response = CodeResponse(
            explanation="Test explanation",
            improved_code="print('hello')",
            changes_made=["Added print statement"]
        )
        self.assertEqual(response.explanation, "Test explanation")
        self.assertEqual(response.improved_code, "print('hello')")
        self.assertEqual(len(response.changes_made), 1)
