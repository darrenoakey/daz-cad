"""
Tests for the string_utils.py module.

This demonstrates the NEW style where tests are in a separate file.
"""
from string_utils import reverse_string, capitalize_words, count_vowels

def test_reverse_string():
    """Test the reverse_string function."""
    assert reverse_string("hello") == "olleh"
    assert reverse_string("world") == "dlrow"
    assert reverse_string("") == ""

def test_capitalize_words():
    """Test the capitalize_words function."""
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("python is great") == "Python Is Great"
    assert capitalize_words("") == ""

def test_count_vowels():
    """Test the count_vowels function."""
    assert count_vowels("hello") == 2
    assert count_vowels("world") == 1
    assert count_vowels("aeiou") == 5
    assert count_vowels("xyz") == 0
