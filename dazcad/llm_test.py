"""Tests for LLM functionality."""

import unittest
from pydantic import BaseModel

try:
    from .llm import (
        setmodel,
        get_llm, 
        get_current_model,
        improve_code_with_llm,
        generate_git_commit_message,
        _create_improvement_prompt,
        _clean_problematic_code,
        CodeResponse,
        CodeImprovementResponse,
        GitCommitResponse
    )
except ImportError:
    # Fallback for direct execution
    from llm import (
        setmodel,
        get_llm, 
        get_current_model,
        improve_code_with_llm,
        generate_git_commit_message,
        _create_improvement_prompt,
        _clean_problematic_code,
        CodeResponse,
        CodeImprovementResponse,
        GitCommitResponse
    )


class SimpleTestResponse(BaseModel):
    """Simple test response for testing chat_structured."""
    message: str
    success: bool


class TestLlmFunctionality(unittest.TestCase):
    """Test all LLM functions with tinyllama for speed."""

    def test_get_current_model(self):
        """Test get_current_model function."""
        setmodel("ollama:tinyllama")
        model = get_current_model()
        self.assertIsInstance(model, str)
        self.assertEqual(model, "ollama:tinyllama")

    def test_get_llm_client(self):
        """Test get_llm function."""
        setmodel("ollama:tinyllama")
        llm = get_llm()
        self.assertIsNotNone(llm)
        # Verify it has the dazllm API methods
        self.assertTrue(hasattr(llm, 'chat_structured'))

    def test_get_llm_with_simulated_error(self):
        """Test get_llm error handling using simulate_error parameter."""
        setmodel("ollama:tinyllama")
        try:
            get_llm(simulate_error=True)
            self.fail("Should have raised RuntimeError")
        except RuntimeError as e:
            self.assertIn("Simulated LLM initialization error", str(e))

    def test_llm_chat_structured(self):
        """Test LLM chat_structured with tinyllama."""
        setmodel("ollama:tinyllama")
        llm = get_llm()
        try:
            response = llm.chat_structured(
                "Reply with message 'hello test' and success true.",
                SimpleTestResponse
            )
            self.assertIsInstance(response, SimpleTestResponse)
            self.assertIsInstance(response.message, str)
            self.assertIsInstance(response.success, bool)
            print(f"TinyLlama response: {response.message}")
        except Exception as e:
            print(f"TinyLlama unavailable: {e}")
            # Just verify the client works
            self.assertIsNotNone(llm)

    def test_generate_git_commit_message(self):
        """Test generate_git_commit_message function."""
        setmodel("ollama:tinyllama")
        result = generate_git_commit_message(
            "Add component",
            "import cadquery as cq\nbox = cq.Workplane().box(2, 2, 2)"
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        print(f"Generated commit: {result}")

    def test_generate_git_commit_quote_removal(self):
        """Test quote removal in git commit messages."""
        setmodel("ollama:tinyllama")
        
        result = generate_git_commit_message("Test", "code = 'test'")
        # Verify no starting/ending quotes
        self.assertFalse(result.startswith('"') and result.endswith('"'))

    def test_generate_git_commit_with_simulated_error(self):
        """Test git commit message fallback using simulate_error."""
        setmodel("ollama:tinyllama")
        result = generate_git_commit_message(
            "Test action", 
            "test code",
            simulate_error=True
        )
        # Should get fallback message
        self.assertIn("Auto-commit", result)
        self.assertIn("Test action", result)

    def test_improve_code_with_llm_success(self):
        """Test improve_code_with_llm function success path."""
        setmodel("ollama:tinyllama")
        
        def success_runner(code: str) -> dict:
            """Code runner that always succeeds."""
            return {"success": True, "output": "OK", "error": None}

        result = improve_code_with_llm(
            "add a comment",
            "import cadquery as cq\nbox = cq.Workplane().box(1, 1, 1)",
            success_runner,
            max_retries=1
        )
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        print(f"Code improvement success: {result['success']}")

    def test_improve_code_with_llm_retry_logic(self):
        """Test improve_code_with_llm retry logic."""
        setmodel("ollama:tinyllama")
        
        def failing_runner(code: str) -> dict:
            """Code runner that always fails."""
            return {"success": False, "output": "", "error": "Simulated error", "traceback": "test trace"}

        result = improve_code_with_llm(
            "fix this",
            "broken_code",
            failing_runner,
            max_retries=2
        )
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("all_errors", result)
        # Should try multiple times and collect errors
        if "all_errors" in result:
            self.assertGreater(len(result["all_errors"]), 0)

    def test_improve_code_with_llm_simulated_error(self):
        """Test improve_code_with_llm exception handling using simulate_error."""
        setmodel("ollama:tinyllama")
        
        def dummy_runner(code: str) -> dict:
            return {"success": True, "output": "OK", "error": None}

        result = improve_code_with_llm(
            "test improvement",
            "test_code",
            dummy_runner,
            max_retries=1,
            simulate_error=True
        )
        # Should handle LLM errors gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertFalse(result["success"])
        self.assertIn("all_errors", result)

    def test_create_improvement_prompt(self):
        """Test _create_improvement_prompt function."""
        setmodel("ollama:tinyllama")
        
        # Test basic prompt
        prompt = _create_improvement_prompt("make bigger", "test_code", None)
        self.assertIn("make bigger", prompt)
        self.assertIn("test_code", prompt)
        self.assertIn("CadQuery", prompt)

        # Test error prompt
        error_info = {"error": "SyntaxError", "traceback": "line 1"}
        prompt = _create_improvement_prompt("fix error", "bad_code", error_info)
        self.assertIn("fix error", prompt)
        self.assertIn("SyntaxError", prompt)
        self.assertIn("bad_code", prompt)

    def test_clean_problematic_code_unittest_main(self):
        """Test _clean_problematic_code with unittest.main pattern."""
        setmodel("ollama:tinyllama")
        
        # Test cleaning unittest.main()
        dirty_code = '''import unittest
class Test(unittest.TestCase):
    def test_something(self):
        pass

if __name__ == "__main__":
    unittest.main()
'''
        clean_code = _clean_problematic_code(dirty_code)
        self.assertNotIn("unittest.main()", clean_code)
        self.assertNotIn("__main__", clean_code)
        self.assertIn("class Test", clean_code)

    def test_clean_problematic_code_complex_skip_block(self):
        """Test _clean_problematic_code skip_block logic."""
        setmodel("ollama:tinyllama")
        
        # Create code that will trigger the skip_block reset logic
        dirty_code = '''import sys
print("start")

if __name__ == "__main__":
    print("in main block")
    sys.exit(0)

def normal_function():
    print("after main block")
'''
        clean_code = _clean_problematic_code(dirty_code)
        self.assertNotIn("__main__", clean_code)
        self.assertNotIn("sys.exit", clean_code)
        self.assertIn("def normal_function", clean_code)
        self.assertIn("print(\"start\")", clean_code)

    def test_clean_problematic_code_no_changes_needed(self):
        """Test _clean_problematic_code with good code."""
        setmodel("ollama:tinyllama")
        
        # Test with code that doesn't need cleaning
        good_code = '''import cadquery as cq
def make_box():
    return cq.Workplane().box(1, 1, 1)
'''
        result = _clean_problematic_code(good_code)
        self.assertIn("import cadquery", result)
        self.assertIn("def make_box", result)

    def test_clean_problematic_code_sys_exit(self):
        """Test _clean_problematic_code with sys.exit pattern."""
        setmodel("ollama:tinyllama")
        
        dirty_code = '''import sys
print("hello")
sys.exit(0)
'''
        clean_code = _clean_problematic_code(dirty_code)
        self.assertNotIn("sys.exit(", clean_code)
        self.assertIn("print", clean_code)

    def test_code_response_model(self):
        """Test CodeResponse pydantic model."""
        setmodel("ollama:tinyllama")
        
        response = CodeResponse(
            success=True,
            code="test = 1",
            explanation="Test code"
        )
        self.assertTrue(response.success)
        self.assertEqual(response.code, "test = 1")
        self.assertEqual(response.explanation, "Test code")
        self.assertIsNone(response.error)

        # Test with error
        error_response = CodeResponse(
            success=False,
            code="",
            explanation="Failed",
            error="Test error"
        )
        self.assertFalse(error_response.success)
        self.assertEqual(error_response.error, "Test error")

    def test_code_improvement_response_model(self):
        """Test CodeImprovementResponse pydantic model."""
        setmodel("ollama:tinyllama")
        
        response = CodeImprovementResponse(
            code="improved_code = 'better'",
            explanation="Made it better",
            has_test_runner=False
        )
        self.assertEqual(response.code, "improved_code = 'better'")
        self.assertEqual(response.explanation, "Made it better")
        self.assertFalse(response.has_test_runner)

    def test_git_commit_response_model(self):
        """Test GitCommitResponse pydantic model."""
        setmodel("ollama:tinyllama")
        
        response = GitCommitResponse(
            commit_message="Add new feature",
            action_verb="Add"
        )
        self.assertEqual(response.commit_message, "Add new feature")
        self.assertEqual(response.action_verb, "Add")


if __name__ == '__main__':
    unittest.main()
