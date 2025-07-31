"""Core functionality for library export testing."""

import unittest
from pathlib import Path
from typing import List, Dict, Any

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

try:
    from .library_manager_core import LibraryManager
except ImportError:
    from library_manager_core import LibraryManager


class LibraryExecutor:
    """Handles execution of library files for testing."""

    def __init__(self, library_path: Path):
        """Initialize the library executor."""
        self.library_path = library_path
        self.library_manager = LibraryManager(built_in_library_path=str(library_path))

    def execute_library_file(self, file_path: Path) -> Dict[str, Any]:
        """Execute a library file and capture shown objects."""
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as file:
            code = file.read()

        # Set up execution environment
        shown_objects = []

        def show_object(obj, name=None, color=None):
            """Capture objects to be displayed."""
            shown_objects.append({
                'object': obj,
                'name': name or f'Object_{len(shown_objects)}',
                'color': color
            })
            return obj

        # Execute the code
        exec_globals = {
            '__name__': '__main__',
            'show_object': show_object,
            'cq': cq if CADQUERY_AVAILABLE else None
        }

        try:
            exec(code, exec_globals)  # pylint: disable=exec-used
        except (SyntaxError, ImportError, NameError, AttributeError, TypeError) as e:
            raise RuntimeError(f"Failed to execute {file_path.name}: {e}") from e
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Catch any other unexpected exceptions during library execution
            raise RuntimeError(f"Unexpected error executing {file_path.name}: {e}") from e

        return {
            'globals': exec_globals,
            'shown_objects': shown_objects
        }

    def get_exportable_objects(self, execution_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract exportable objects from execution result."""
        exportable_objects = []

        # Add shown objects
        for shown_obj in execution_result['shown_objects']:
            obj = shown_obj['object']
            if self.is_exportable_object(obj):
                exportable_objects.append({
                    'object': obj,
                    'name': shown_obj['name'],
                    'type': self.get_object_type(obj)
                })

        # Look for other exportable objects in globals
        for name, obj in execution_result['globals'].items():
            if (not name.startswith('_') and
                name not in ['cq', 'show_object'] and
                self.is_exportable_object(obj)):
                exportable_objects.append({
                    'object': obj,
                    'name': name,
                    'type': self.get_object_type(obj)
                })

        return exportable_objects

    def is_exportable_object(self, obj: Any) -> bool:
        """Check if an object can be exported."""
        if not CADQUERY_AVAILABLE:
            return False

        return (hasattr(obj, 'val') or  # CadQuery Workplane/Shape
                isinstance(obj, cq.Assembly) or  # CadQuery Assembly
                hasattr(obj, 'wrapped'))  # Other CadQuery objects

    def get_object_type(self, obj: Any) -> str:
        """Get the type of an exportable object."""
        if not CADQUERY_AVAILABLE:
            return 'unknown'

        if isinstance(obj, cq.Assembly):
            return 'assembly'
        return 'shape'


class TestLibraryExecutor(unittest.TestCase):
    """Tests for LibraryExecutor."""

    def test_library_executor_creation(self):
        """Test that LibraryExecutor can be created."""
        library_path = Path(__file__).parent / "library"
        executor = LibraryExecutor(library_path)
        self.assertIsInstance(executor, LibraryExecutor)
        self.assertEqual(executor.library_path, library_path)

    def test_is_exportable_object(self):
        """Test exportable object detection."""
        library_path = Path(__file__).parent / "library"
        executor = LibraryExecutor(library_path)

        # Test with None
        self.assertFalse(executor.is_exportable_object(None))

        # Test with string
        self.assertFalse(executor.is_exportable_object("test"))

    def test_get_object_type(self):
        """Test object type detection."""
        library_path = Path(__file__).parent / "library"
        executor = LibraryExecutor(library_path)

        # Test with None
        result = executor.get_object_type(None)
        self.assertIsNotNone(result)

    def test_get_exportable_objects(self):
        """Test extracting exportable objects."""
        library_path = Path(__file__).parent / "library"
        executor = LibraryExecutor(library_path)

        execution_result = {
            'globals': {'test': 'value'},
            'shown_objects': []
        }

        objects = executor.get_exportable_objects(execution_result)
        self.assertIsInstance(objects, list)
