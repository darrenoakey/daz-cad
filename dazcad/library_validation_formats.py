"""Format-specific validation functions for exported data.

This module contains validators for different export formats (STL, STEP, 3MF).
"""

import unittest
from typing import Tuple


def validate_export_data(data: bytes, format_name: str) -> Tuple[bool, str]:
    """Validate exported data for a specific format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation
    if not isinstance(data, bytes):
        return False, f"Export did not return bytes, got {type(data).__name__}"

    if len(data) == 0:
        return False, "Export returned empty data"

    # Additional sanity check - verify it's not just whitespace
    if len(data.strip()) == 0:
        return False, "Export returned only whitespace"

    # Format-specific validation with minimum size requirements
    format_validators = {
        'stl': validate_stl_data,
        'step': validate_step_data,
        '3mf': validate_3mf_data
    }

    validator = format_validators.get(format_name)
    if validator:
        return validator(data)

    # For unknown formats, enforce minimum size
    if len(data) < 50:  # Minimum reasonable file size
        return False, (f"Export data too small for any valid {format_name} file: "
                      f"{len(data)} bytes")

    return True, ""


def validate_stl_data(data: bytes) -> Tuple[bool, str]:
    """Validate STL format data."""
    # Check minimum size first
    min_size = 84  # Minimum binary STL size (80-byte header + 4-byte triangle count)
    if len(data) < min_size:
        return False, f"STL data too small: {len(data)} bytes (minimum {min_size} bytes)"

    # Check for valid STL format
    if data.startswith(b'solid'):
        # ASCII STL - should have actual content, not just header
        if data.count(b'facet normal') == 0:
            return False, "ASCII STL missing facet data - likely just a placeholder"
        if len(data) < 200:  # Minimum reasonable ASCII STL with actual geometry
            return False, f"ASCII STL too small for actual geometry: {len(data)} bytes"
    else:
        # Binary STL - check we have at least proper header
        if len(data) < 84:
            return False, f"Binary STL incomplete: {len(data)} bytes"

    return True, ""


def validate_step_data(data: bytes) -> Tuple[bool, str]:
    """Validate STEP format data."""
    # Check minimum size first
    min_size = 500  # Minimum reasonable STEP file with actual geometry
    if len(data) < min_size:
        return False, (f"STEP data too small for valid file: {len(data)} bytes "
                      f"(minimum {min_size} bytes)")

    # Check for required STEP headers
    if b'ISO-10303' not in data:
        return False, "Invalid STEP format - missing ISO-10303 header"

    # Check for actual geometry data (not just placeholder)
    if b'CARTESIAN_POINT' not in data and b'VERTEX_POINT' not in data:
        return False, "STEP file missing geometry data - likely just a placeholder"

    return True, ""


def validate_3mf_data(data: bytes) -> Tuple[bool, str]:
    """Validate 3MF format data."""
    # Check minimum size first
    min_size = 1000  # Minimum reasonable 3MF file (it's a ZIP with XML)
    if len(data) < min_size:
        return False, (f"3MF data too small for valid archive: {len(data)} bytes "
                      f"(minimum {min_size} bytes)")

    # Check it's a ZIP file
    if not data.startswith(b'PK'):
        return False, "Invalid 3MF format - not a ZIP archive"

    return True, ""


class TestFormatValidation(unittest.TestCase):
    """Tests for format-specific validation functions."""

    def test_validate_export_data_stl(self):
        """Test STL format validation."""
        # Valid ASCII STL with actual geometry - make it larger than 200 bytes
        stl_data = (b'solid test\nfacet normal 0 0 1\n  outer loop\n    vertex 0 0 0\n'
                   b'    vertex 1 0 0\n    vertex 0 1 0\n  endloop\nendfacet\n'
                   b'facet normal 0 0 1\n  outer loop\n    vertex 1 0 0\n'
                   b'    vertex 1 1 0\n    vertex 0 1 0\n  endloop\nendfacet\n'
                   b'endsolid test')
        valid, error = validate_export_data(stl_data, 'stl')
        self.assertTrue(valid, f"Should accept valid ASCII STL: {error}")

        # Valid binary STL (at least 84 bytes with data)
        binary_stl = b'x' * 84 + b'additional geometry data' * 10  # Make it substantial
        valid, error = validate_export_data(binary_stl, 'stl')
        self.assertTrue(valid, f"Should accept substantial binary STL: {error}")

        # Invalid STL - too small
        valid, error = validate_export_data(b'small', 'stl')
        self.assertFalse(valid)
        self.assertIn("too small", error)

    def test_validate_export_data_step(self):
        """Test STEP format validation."""
        # Valid STEP with actual geometry - make it larger than 500 bytes
        step_data = (b'ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n'
                    b'#1=CARTESIAN_POINT(\'\',(1.0,2.0,3.0));\n' + b'x' * 500 +
                    b'\nENDSEC;\nEND-ISO-10303-21;')
        valid, error = validate_export_data(step_data, 'step')
        self.assertTrue(valid, f"Should accept valid STEP: {error}")

        # Invalid STEP - too small
        valid, error = validate_export_data(b'ISO-10303-21;', 'step')
        self.assertFalse(valid)
        self.assertIn("too small", error)

    def test_validate_export_data_3mf(self):
        """Test 3MF format validation."""
        # Valid 3MF (ZIP file) - needs to be substantial
        valid_3mf = b'PK\x03\x04' + b'x' * 1000  # ZIP header plus content
        valid, error = validate_export_data(valid_3mf, '3mf')
        self.assertTrue(valid, f"Should accept valid 3MF: {error}")

        # Invalid 3MF - too small
        valid, error = validate_export_data(b'PK\x03\x04', '3mf')
        self.assertFalse(valid)
        self.assertIn("too small", error)
