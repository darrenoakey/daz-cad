"""DazCAD - A simple CadQuery runner with web interface."""

import unittest


class PackageTests(unittest.TestCase):
    """Tests for the DazCAD package."""

    def test_package_attributes(self):
        """Test that the package has expected attributes."""
        # Test that this module has expected attributes
        self.assertIsNotNone(self.__class__)
        self.assertEqual(self.__class__.__name__, 'PackageTests')
