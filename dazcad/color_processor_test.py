"""Tests for color processing utilities."""

import unittest

from .color_processor import process_child_color


class TestColorProcessor(unittest.TestCase):
    """Tests for color processing utilities."""

    def test_process_string_color(self):
        """Test processing string colors."""
        result = process_child_color("#ff0000")
        self.assertEqual(result, "#ff0000")

    def test_process_tuple_color(self):
        """Test processing tuple colors."""
        result = process_child_color((1.0, 0.0, 0.0, 1.0))
        self.assertEqual(result, "#ff0000")

    def test_process_list_color(self):
        """Test processing list colors."""
        result = process_child_color([0.0, 1.0, 0.0, 1.0])
        self.assertEqual(result, "#00ff00")

    def test_process_none_color(self):
        """Test processing None color."""
        result = process_child_color(None)
        self.assertEqual(result, "#808080")  # Default gray

    def test_process_unexpected_type(self):
        """Test processing unexpected color type."""
        result = process_child_color(42)  # Integer
        self.assertEqual(result, "42")  # Should convert to string

    def test_process_complex_object(self):
        """Test processing complex object without toTuple."""
        result = process_child_color({"r": 1, "g": 0, "b": 0})  # Dict
        self.assertEqual(result, "{'r': 1, 'g': 0, 'b': 0}")  # Should convert to string


if __name__ == '__main__':
    unittest.main()
