"""Tests for chat route handlers."""

import unittest

try:
    from .server_routes_chat import chat_with_ai
except ImportError:
    # Fallback for direct execution
    from server_routes_chat import chat_with_ai


class TestChatRoutes(unittest.TestCase):
    """Tests for chat route handlers."""

    def test_chat_with_ai_function_structure(self):
        """Test that chat_with_ai function has expected structure."""
        # Test that the function exists by checking its attributes
        self.assertTrue(hasattr(chat_with_ai, '__name__'))
        self.assertEqual(chat_with_ai.__name__, 'chat_with_ai')
        self.assertTrue(hasattr(chat_with_ai, '__doc__'))
        self.assertIsNotNone(chat_with_ai.__doc__)


if __name__ == '__main__':
    unittest.main()
