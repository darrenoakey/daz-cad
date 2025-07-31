"""Quick test to verify library file validation works correctly."""

import unittest
from pathlib import Path

try:
    from .cadquery_file_validator import validate_cadquery_file
except ImportError:
    from cadquery_file_validator import validate_cadquery_file


class TestLibraryFileValidationWorks(unittest.TestCase):
    """Test that our validation system works on actual library files."""

    def test_validate_bearing_file(self):
        """Test validation on the bearing.py library file."""
        library_path = Path(__file__).parent / "library"
        bearing_file = library_path / "bearing.py"

        # Make sure the file exists
        self.assertTrue(bearing_file.exists(),
                       f"Bearing file not found at {bearing_file}")

        # Validate the file
        result = validate_cadquery_file(bearing_file, verbose=True)

        # Check the result structure
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('file', result)
        self.assertIn('execution_error', result)
        self.assertIn('objects', result)
        self.assertIn('summary', result)

        # The file should execute without errors
        self.assertEqual(result['execution_error'], '',
                        f"Execution error: {result['execution_error']}")

        # Should have found objects
        self.assertGreater(result['summary']['total_objects'], 0,
                          "No objects found in bearing.py")

        print("\nValidation result for bearing.py:")
        print(f"  Total objects: {result['summary']['total_objects']}")
        print(f"  Valid objects: {result['summary']['valid_objects']}")
        print(f"  Total export tests: {result['summary']['total_export_tests']}")
        print(f"  Successful exports: {result['summary']['successful_exports']}")

        if result['success']:
            print("  ✅ Validation successful!")
        else:
            print("  ⚠️  Validation completed with issues")

    def test_validate_vase_file(self):
        """Test validation on the vase.py library file."""
        library_path = Path(__file__).parent / "library"
        vase_file = library_path / "vase.py"

        # Make sure the file exists
        self.assertTrue(vase_file.exists(),
                       f"Vase file not found at {vase_file}")

        # Validate the file
        result = validate_cadquery_file(vase_file, verbose=False)

        # The file should execute without errors
        self.assertEqual(result['execution_error'], '',
                        f"Execution error: {result['execution_error']}")

        # Should have found objects
        self.assertGreater(result['summary']['total_objects'], 0,
                          "No objects found in vase.py")
