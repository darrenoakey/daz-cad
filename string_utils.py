"""
Simple string utilities module (NEW style).

This demonstrates the new style where tests are in a separate file.
No embedded tests here - they've been moved to string_utils_test.py
"""

def reverse_string(s):
    """Reverse a string."""
    return s[::-1]

def capitalize_words(s):
    """Capitalize the first letter of each word."""
    return ' '.join(word.capitalize() for word in s.split())

def count_vowels(s):
    """Count the number of vowels in a string."""
    vowels = 'aeiouAEIOU'
    return sum(1 for char in s if char in vowels)
