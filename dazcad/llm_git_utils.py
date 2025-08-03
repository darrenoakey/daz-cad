"""LLM-powered git commit message generation."""

import unittest

try:
    from .llm_client import get_llm
except ImportError:
    from llm_client import get_llm


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

        response = llm.chat(prompt)

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


class TestGitCommitGeneration(unittest.TestCase):
    """Tests for git commit message generation."""

    def test_generate_commit_message_function_exists(self):
        """Test that generate_git_commit_message function exists."""
        self.assertTrue(callable(generate_git_commit_message))

    def test_generate_commit_message_fallback(self):
        """Test commit message generation fallback."""
        # When LLM is not available, should return fallback
        result = generate_git_commit_message("Test action", "test code")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_generate_commit_message_with_empty_inputs(self):
        """Test commit message generation with empty inputs."""
        result = generate_git_commit_message("", "")
        self.assertIsInstance(result, str)
        # Should still return something reasonable
        self.assertGreater(len(result), 0)

    def test_generate_commit_uses_chat_not_invoke(self):
        """Test that git commit generation uses chat() method, not invoke()."""
        llm = get_llm()
        if llm is not None:
            # Verify the LLM has chat method and not invoke
            self.assertTrue(hasattr(llm, 'chat'),
                          "LLM should have 'chat' method for dazllm API")
            self.assertFalse(hasattr(llm, 'invoke'),
                           "LLM should NOT have 'invoke' method")
            
            # Test that calling generate_git_commit_message doesn't fail with AttributeError
            try:
                result = generate_git_commit_message("Test commit", "test = 1")
                self.assertIsInstance(result, str)
            except AttributeError as e:
                # Should not fail due to missing 'chat' method
                error_msg = str(e)
                self.assertNotIn("'invoke'", error_msg,
                               "Error should not be about missing 'invoke' method")
                self.assertNotIn("has no attribute 'chat'", error_msg,
                               "LLM should have 'chat' method")
