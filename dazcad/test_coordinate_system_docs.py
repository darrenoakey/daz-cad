"""Test for coordinate system documentation files."""

import os
import unittest


class TestCoordinateSystemDocs(unittest.TestCase):
    """Tests for coordinate system documentation."""

    def test_main_documentation_file_exists(self):
        """Test that the main coordinate system documentation file exists."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        docs_file = os.path.join(test_dir, 'coordinate_system_docs.js')

        self.assertTrue(os.path.exists(docs_file),
                       "coordinate_system_docs.js should exist")

    def test_debug_documentation_file_exists(self):
        """Test that the debug documentation file exists."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        debug_file = os.path.join(test_dir, 'coordinate_system_debug.js')

        self.assertTrue(os.path.exists(debug_file),
                       "coordinate_system_debug.js should exist")

    def test_documentation_files_have_content(self):
        """Test that the documentation files have substantial content."""
        test_dir = os.path.dirname(os.path.abspath(__file__))

        for filename in ['coordinate_system_docs.js', 'coordinate_system_debug.js']:
            docs_file = os.path.join(test_dir, filename)

            if os.path.exists(docs_file):
                with open(docs_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Should contain key coordinate system terms
                self.assertIn('coordinate', content.lower())
                self.assertIn('three.js', content.lower())

                # Should be substantial documentation (more than 500 characters)
                self.assertGreater(len(content), 500,
                                 f"{filename} should be comprehensive")

    def test_critical_warnings_present(self):
        """Test that critical warnings are present in documentation."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        docs_file = os.path.join(test_dir, 'coordinate_system_docs.js')

        if os.path.exists(docs_file):
            with open(docs_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Should contain critical warnings
            self.assertIn('CRITICAL', content.upper())
            self.assertIn('WARNING', content.upper())

    def test_debug_file_has_debugging_guidance(self):
        """Test that debug file contains debugging guidance."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        debug_file = os.path.join(test_dir, 'coordinate_system_debug.js')

        if os.path.exists(debug_file):
            with open(debug_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Should contain debugging guidance
            self.assertIn('DEBUGGING', content.upper())
            self.assertIn('MISTAKE', content.upper())
            self.assertIn('console.log', content.lower())
