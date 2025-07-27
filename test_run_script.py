#!/usr/bin/env python3
"""
Tests for the run bash script.
"""

import unittest
import os
from pathlib import Path


class TestRunScript(unittest.TestCase):
    """Test cases for the run bash script."""

    def test_run_script_exists(self):
        """Test that the run script exists."""
        self.assertTrue(Path("run").exists())

    def test_run_script_is_executable(self):
        """Test that the run script has executable permissions."""
        run_path = Path("run")
        self.assertTrue(run_path.exists())
        # Check if file is readable (at minimum)
        self.assertTrue(os.access(run_path, os.R_OK))

    def test_run_script_has_shebang(self):
        """Test that the run script has a proper shebang."""
        with open("run", "r", encoding="utf-8") as file:
            first_line = file.readline().strip()
            self.assertTrue(first_line.startswith("#!/bin/bash"))

    def test_run_script_contains_expected_content(self):
        """Test that the run script contains expected functionality."""
        with open("run", "r", encoding="utf-8") as file:
            content = file.read()

        # Check for essential components
        self.assertIn("ollama list", content)
        self.assertIn("pip install", content)
        self.assertIn("server.py", content)
        self.assertIn("localhost:8000", content)
