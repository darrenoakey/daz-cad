"""Color processing utilities for DazCAD."""

import traceback
import unittest

# Import core utilities with fallback for direct execution
try:
    from .cadquery_core import color_to_hex
except ImportError:
    from cadquery_core import color_to_hex


def process_child_color(child_color):
    """Process a child's color attribute and return hex color string.
    
    Args:
        child_color: The color attribute from an assembly child
        
    Returns:
        Hex color string like '#ff0000'
    """
    # Initialize with default gray
    part_color = color_to_hex(None)
    
    if child_color:
        try:
            print(f"  Child color: {child_color} (type: {type(child_color)})")
            
            # Check for string first (most explicit)
            if isinstance(child_color, str):
                part_color = child_color
                print(f"  Using string color: {part_color}")
            # Check for tuple/list
            elif isinstance(child_color, (tuple, list)):
                part_color = color_to_hex(child_color)
                print(f"  Converted tuple color: {part_color}")
            # Check for CadQuery Color object - be very explicit
            elif (hasattr(child_color, 'toTuple') and
                  callable(getattr(child_color, 'toTuple'))):
                # Double-check it's not a string with a toTuple method somehow
                if not isinstance(child_color, str):
                    color_tuple = child_color.toTuple()
                    part_color = color_to_hex(color_tuple)
                    print(f"  Converted CadQuery color: {part_color}")
                else:
                    print(f"  Warning: String has toTuple method: {child_color}")
                    part_color = child_color
            else:
                msg = f"  Unexpected color type: {type(child_color)}, using as string"
                print(msg)
                part_color = str(child_color)
                
        except (AttributeError, TypeError, ValueError) as color_error:
            print(f"  Error processing color: {color_error}")
            print(f"  Color value: {child_color}")
            print(f"  Color type: {type(child_color)}")
            traceback.print_exc()
            part_color = color_to_hex(None)  # Fall back to default
    
    return part_color


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

    def test_process_none_color(self):
        """Test processing None color."""
        result = process_child_color(None)
        self.assertEqual(result, "#808080")  # Default gray
