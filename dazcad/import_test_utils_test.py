"""Tests for ImportUtils class."""

import unittest
from pathlib import Path

from .import_test_utils import ImportUtils


class TestImportUtils(unittest.TestCase):
    """Tests for ImportUtils class."""

    def test_import_utils_creation(self):
        """Test that ImportUtils can be created."""
        test_dir = Path(__file__).parent
        utils = ImportUtils(test_dir)
        self.assertIsNotNone(utils)
        self.assertEqual(utils.test_dir, test_dir)

    def test_find_python_files(self):
        """Test finding Python files."""
        test_dir = Path(__file__).parent
        utils = ImportUtils(test_dir)
        files = utils.find_python_files()
        self.assertIsInstance(files, list)
        self.assertGreater(len(files), 0)

    def test_known_imports_structure(self):
        """Test that known imports test returns proper structure."""
        test_dir = Path(__file__).parent
        utils = ImportUtils(test_dir)
        results = utils.test_known_imports()
        self.assertIsInstance(results, list)
        for result in results:
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 3)
            module_name, success, _ = result  # Don't need error for this test
            self.assertIsInstance(module_name, str)
            self.assertIsInstance(success, bool)


if __name__ == '__main__':
    unittest.main()
