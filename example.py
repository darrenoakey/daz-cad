"""
Simple math utilities module.

This demonstrates the new style where tests are in a separate file.
"""

def add(a, b):
    """Add two numbers together."""
    return a + b

def multiply(a, b):
    """Multiply two numbers together."""
    return a * b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
