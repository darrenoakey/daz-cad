"""LLM-powered code improvement functionality."""

import unittest
from typing import Callable

try:
    from .llm_client import get_llm
except ImportError:
    from llm_client import get_llm


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

        response = llm.chat(prompt)

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


class TestCodeImprovement(unittest.TestCase):
    """Tests for code improvement functionality."""

    def test_improve_code_function_exists(self):
        """Test that improve_code_with_llm function exists."""
        self.assertTrue(callable(improve_code_with_llm))

    def test_improve_code_with_real_runner(self):
        """Test code improvement with real code runner."""
        # Real code runner that checks if code has basic structure
        def real_runner(code):
            try:
                # Basic validation that code has expected structure
                if "cq.Workplane" in code and "box" in code:
                    return {"success": True, "objects": []}
                return {"success": False, "error": "Invalid CadQuery code"}
            except (ValueError, TypeError, AttributeError) as e:
                return {"success": False, "error": str(e)}

        result = improve_code_with_llm(
            "make it bigger", 
            "box = cq.Workplane().box(1,1,1)",
            real_runner
        )

        # Should handle gracefully regardless of LLM availability
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("response", result)
        self.assertIn("code", result)

    def test_improve_code_with_failing_runner(self):
        """Test code improvement with failing code runner."""
        # Real code runner that always fails
        def failing_runner(_code):
            return {"success": False, "error": "Code execution failed"}

        result = improve_code_with_llm(
            "add a sphere",
            "box = cq.Workplane().box(1,1,1)",
            failing_runner
        )

        # Should handle runner failures gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("response", result)
        self.assertIn("code", result)
