"""LLM-powered git commit message generation."""

import unittest

from pydantic import BaseModel, Field

try:
    from .llm_client import get_llm
except ImportError:
    from llm_client import get_llm


class GitCommitResponse(BaseModel):
    """Structured response for git commit message generation."""
    commit_message: str = Field(description="Concise git commit message under 50 characters")
    action_verb: str = Field(description="The action verb used (Add, Update, Fix, Create, etc.)")


def generate_git_commit_message(action: str, code_content: str) -> str:
    """Generate a descriptive git commit message using LLM.

    Args:
        action: The action being performed (e.g., "Updated example")
        code_content: The code content to analyze

    Returns:
        Generated commit message or fallback message
    """
    llm = get_llm()
    try:
        # Create a prompt for generating commit message
        prompt = f"""Analyze this CadQuery code and generate a concise git commit message.

Action: {action}

Code:
{code_content[:1000]}

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

Provide the commit message and the action verb used."""

        response = llm.chat_structured(prompt, GitCommitResponse)

        # Use the structured response
        commit_msg = response.commit_message.strip()

        # Clean up the response - remove quotes if present
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

    def test_generate_commit_uses_chat_structured(self):
        """Test that git commit generation uses chat_structured method."""
        llm = get_llm()
        # Verify the LLM has chat_structured method
        self.assertTrue(hasattr(llm, 'chat_structured'),
                      "LLM should have 'chat_structured' method for dazllm API")
        
        # Test that calling generate_git_commit_message works
        try:
            result = generate_git_commit_message("Test commit", "test = 1")
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
        except AttributeError as e:
            # Should not fail due to missing methods
            error_msg = str(e)
            self.assertNotIn("'invoke'", error_msg,
                           "Error should not be about missing 'invoke' method")
            self.assertNotIn("has no attribute 'chat_structured'", error_msg,
                           "LLM should have 'chat_structured' method")

    def test_git_commit_response_model(self):
        """Test GitCommitResponse model."""
        response = GitCommitResponse(
            commit_message="Add test component",
            action_verb="Add"
        )
        self.assertIsInstance(response.commit_message, str)
        self.assertIsInstance(response.action_verb, str)
        self.assertLessEqual(len(response.commit_message), 50)
