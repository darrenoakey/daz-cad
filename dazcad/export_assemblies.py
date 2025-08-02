"""Assembly export utilities for CadQuery objects."""

import os
import tempfile
import unittest


def export_assembly_to_format(assembly, format_name: str) -> bytes:
    """Export a CadQuery assembly to specified format.

    Args:
        assembly: CadQuery assembly to export
        format_name: Target format (stl, step, 3mf)

    Returns:
        Exported data as bytes

    Raises:
        AttributeError: If the assembly doesn't have required methods
        ValueError: If the format is not supported or export fails
        ImportError: If CadQuery is not available
    """
    try:
        import cadquery as cq  # pylint: disable=import-outside-toplevel,unused-import
    except ImportError as e:
        raise ImportError("CadQuery is required for export operations") from e

    format_lower = format_name.lower()

    # Convert assembly to compound first
    compound = assembly.toCompound()

    # Export based on format using cq.exporters.export
    with tempfile.NamedTemporaryFile(suffix=f'.{format_lower}', delete=False) as tmp_file:
        tmp_filename = tmp_file.name

    try:
        if format_lower == "stl":
            cq.exporters.export(compound, tmp_filename, exportType="STL")
        elif format_lower == "step":
            cq.exporters.export(compound, tmp_filename, exportType="STEP")
        elif format_lower == "3mf":
            # 3MF support may vary by CadQuery version
            try:
                cq.exporters.export(compound, tmp_filename, exportType="3MF")
            except Exception as e:
                os.unlink(tmp_filename)
                raise ValueError(f"3MF export not supported in this CadQuery version: {e}") from e
        else:
            os.unlink(tmp_filename)
            raise ValueError(f"Assembly export format '{format_name}' is not supported")

        # Read the exported file
        with open(tmp_filename, 'rb') as f:
            result = f.read()

        # Clean up temporary file
        os.unlink(tmp_filename)

    except Exception as e:
        # Clean up temporary file on error
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
        raise e

    # Validate result has meaningful content
    if len(result) < 10:  # Minimum meaningful content
        raise ValueError(f"Assembly export to {format_name} returned insufficient data: "
                        f"{len(result)} bytes")

    return result


class TestAssemblyExports(unittest.TestCase):
    """Tests for assembly export utilities."""

    def test_export_assembly_to_format_with_invalid_input(self):
        """Test exporting assembly to format with invalid input."""
        # Test with None should raise AttributeError
        with self.assertRaises(AttributeError):
            export_assembly_to_format(None, "stl")

    def test_assembly_export_functions_exist(self):
        """Test that assembly export functions exist."""
        self.assertTrue(callable(export_assembly_to_format))
