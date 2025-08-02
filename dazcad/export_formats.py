"""Export format definitions and utilities for CadQuery objects."""

import os
import tempfile
import unittest
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable


@dataclass
class ExportFormat:
    """Represents an export format configuration."""
    extension: str
    mime_type: str
    description: str
    supports_colors: bool = False
    assembly_handler: Optional[Callable] = None

    @property
    def name(self) -> str:
        """Get the format name (uppercase extension)."""
        return self.extension.upper()

    def supports_assemblies(self) -> bool:
        """Check if this format supports assemblies."""
        return self.assembly_handler is not None

    def set_assembly_handler(self, handler: Callable) -> None:
        """Set the assembly handler for this format."""
        object.__setattr__(self, 'assembly_handler', handler)


def get_all_export_formats() -> List[ExportFormat]:
    """Get list of all supported export format objects.

    Returns:
        List of ExportFormat objects
    """
    try:
        import cadquery as cq  # pylint: disable=import-outside-toplevel,unused-import

        def export_assembly_step(a):
            """Export assembly to STEP format."""
            compound = a.toCompound()
            # Use the proper STEP export method
            with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as tmp:
                tmp_name = tmp.name
            cq.exporters.export(compound, tmp_name, exportType="STEP")
            with open(tmp_name, 'rb') as f:
                data = f.read()
            os.unlink(tmp_name)
            return data

        return [
            ExportFormat("stl", "application/octet-stream", "STL 3D Model", False),
            ExportFormat("step", "application/step", "STEP 3D Model", True,
                        export_assembly_step),
            ExportFormat("3mf", "application/3mf", "3MF 3D Model", True),
        ]
    except ImportError:
        # If CadQuery is not available, return basic formats without assembly handlers
        return [
            ExportFormat("stl", "application/octet-stream", "STL 3D Model", False),
            ExportFormat("step", "application/step", "STEP 3D Model", True),
            ExportFormat("3mf", "application/3mf", "3MF 3D Model", True),
        ]


def get_supported_formats() -> List[str]:
    """Get list of supported export format extensions as strings.

    Returns:
        List of format extension strings
    """
    return [fmt.extension for fmt in get_all_export_formats()]


def get_supported_export_formats() -> Dict[str, ExportFormat]:
    """Get dictionary of supported export formats keyed by extension.

    Returns:
        Dictionary mapping extensions to ExportFormat objects
    """
    return {fmt.extension: fmt for fmt in get_all_export_formats()}


def get_format_by_name(name: str) -> Optional[ExportFormat]:
    """Get export format by name.

    Args:
        name: Format name/extension

    Returns:
        ExportFormat object or None if not found
    """
    for fmt in get_all_export_formats():
        if fmt.extension.lower() == name.lower():
            return fmt
    return None


class TestExportFormats(unittest.TestCase):
    """Tests for export format utilities."""

    def test_get_supported_formats(self):
        """Test getting supported formats."""
        formats = get_supported_formats()
        self.assertIsInstance(formats, list)
        self.assertGreater(len(formats), 0)
        self.assertIn("stl", formats)

    def test_get_supported_export_formats(self):
        """Test getting export format extensions."""
        formats = get_supported_export_formats()
        self.assertIsInstance(formats, dict)
        self.assertIn("stl", formats)

    def test_get_format_by_name(self):
        """Test getting format by name."""
        fmt = get_format_by_name("stl")
        self.assertIsInstance(fmt, ExportFormat)
        self.assertEqual(fmt.extension, "stl")

    def test_export_format_properties(self):
        """Test ExportFormat properties."""
        fmt = ExportFormat("test", "application/test", "Test Format")
        self.assertEqual(fmt.name, "TEST")
        self.assertFalse(fmt.supports_assemblies())
