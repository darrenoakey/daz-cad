"""Core LLM functionality for DazCAD."""

from typing import Optional

from pydantic import BaseModel

# Import LLM functionality from specialized modules
try:
    from .llm_client import get_llm, get_current_model
    from .llm_code_improvement import improve_code_with_llm
    from .llm_git_utils import generate_git_commit_message
except ImportError:
    # Fallback for direct execution
    from llm_client import get_llm, get_current_model
    from llm_code_improvement import improve_code_with_llm
    from llm_git_utils import generate_git_commit_message


class CodeResponse(BaseModel):
    """Response model for code generation from LLM."""
    success: bool
    code: str
    explanation: str
    error: Optional[str] = None


# Explicitly define what's available for import from this module
__all__ = [
    'CodeResponse',
    'get_llm',
    'get_current_model', 
    'improve_code_with_llm',
    'generate_git_commit_message'
]
