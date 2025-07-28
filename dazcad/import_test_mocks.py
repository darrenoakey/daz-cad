"""Mock utilities for import testing."""

import sys
import unittest


class MockUtils:
    """Utility class for creating mock modules for testing."""

    @staticmethod
    def create_mock_cadquery():
        """Create a mock cadquery module for testing."""
        # pylint: disable=too-few-public-methods,unused-argument
        class MockModule:
            """Mock cadquery module."""
            class Workplane:
                """Mock Workplane class."""
                def __init__(self, *args, **kwargs):
                    pass
                def box(self, *args, **kwargs):
                    """Mock box method."""
                    return self
                def workplane(self, *args, **kwargs):
                    """Mock workplane method."""
                    return self

            class Assembly:
                """Mock Assembly class."""
                def __init__(self, *args, **kwargs):
                    self.children = []
                def add(self, *args, **kwargs):
                    """Mock add method."""

            class exporters:  # pylint: disable=invalid-name
                """Mock exporters class."""
                class ExportTypes:
                    """Mock ExportTypes class."""
                    STL = "STL"
                    STEP = "STEP"
                    THREEMF = "THREEMF"

                @staticmethod
                def export(*args, **kwargs):
                    """Mock export method."""

        return MockModule()

    @staticmethod
    def create_mock_sanic():
        """Create a mock sanic module for testing."""
        # pylint: disable=too-few-public-methods,unused-argument
        class MockModule:
            """Mock sanic module."""
            class Sanic:
                """Mock Sanic class."""
                def __init__(self, *args, **kwargs):
                    pass
                def route(self, *args, **kwargs):
                    """Mock route decorator."""
                    def decorator(func):
                        return func
                    return decorator

            class response:  # pylint: disable=invalid-name
                """Mock response class."""
                @staticmethod
                def file(*args, **kwargs):
                    """Mock file response."""
                    return MockResponse()

                @staticmethod
                def raw(*args, **kwargs):
                    """Mock raw response."""
                    return MockResponse()

                @staticmethod
                def json(*args, **kwargs):
                    """Mock json response."""
                    return MockResponse()

        class MockResponse:
            """Mock response class."""
            def __init__(self):
                self.headers = {}

        return MockModule()

    @staticmethod
    def install_mocks(mock_modules):
        """Install mock modules and return original modules."""
        original_modules = {}
        for name, mock_module in mock_modules.items():
            if name in sys.modules:
                original_modules[name] = sys.modules[name]
            sys.modules[name] = mock_module
        return original_modules

    @staticmethod
    def restore_mocks(mock_modules, original_modules):
        """Restore original modules."""
        # Restore original modules
        for name, original_module in original_modules.items():
            sys.modules[name] = original_module

        # Remove mock modules that weren't there originally
        for name in mock_modules:
            if name not in original_modules and name in sys.modules:
                del sys.modules[name]


class TestImportTestMocks(unittest.TestCase):
    """Tests for import test mocks module."""

    def test_mock_utils_creation(self):
        """Test that MockUtils can be created."""
        utils = MockUtils()
        self.assertIsNotNone(utils)

    def test_create_mock_cadquery(self):
        """Test creating mock cadquery module."""
        mock_cq = MockUtils.create_mock_cadquery()
        self.assertTrue(hasattr(mock_cq, 'Workplane'))
        self.assertTrue(hasattr(mock_cq, 'Assembly'))
        self.assertTrue(hasattr(mock_cq, 'exporters'))

        # Test Workplane functionality
        workplane = mock_cq.Workplane()
        self.assertEqual(workplane.box(), workplane)
        self.assertEqual(workplane.workplane(), workplane)

        # Test Assembly functionality
        assembly = mock_cq.Assembly()
        self.assertIsInstance(assembly.children, list)

        # Test exporters
        self.assertEqual(mock_cq.exporters.ExportTypes.STL, "STL")
        self.assertEqual(mock_cq.exporters.ExportTypes.STEP, "STEP")
        self.assertEqual(mock_cq.exporters.ExportTypes.THREEMF, "THREEMF")

    def test_create_mock_sanic(self):
        """Test creating mock sanic module."""
        mock_sanic = MockUtils.create_mock_sanic()
        self.assertTrue(hasattr(mock_sanic, 'Sanic'))
        self.assertTrue(hasattr(mock_sanic, 'response'))

        # Test Sanic functionality
        app = mock_sanic.Sanic()
        decorator = app.route('/test')
        self.assertIsNotNone(decorator)

        # Test response functionality
        file_response = mock_sanic.response.file()
        raw_response = mock_sanic.response.raw()
        json_response = mock_sanic.response.json()
        self.assertIsNotNone(file_response)
        self.assertIsNotNone(raw_response)
        self.assertIsNotNone(json_response)

    def test_install_and_restore_mocks(self):
        """Test installing and restoring mock modules."""
        # Create test mocks
        test_mock = type('TestMock', (), {})()
        mock_modules = {'test_mock_module': test_mock}

        # Install mocks
        original_modules = MockUtils.install_mocks(mock_modules)
        self.assertIn('test_mock_module', sys.modules)
        self.assertEqual(sys.modules['test_mock_module'], test_mock)

        # Restore mocks
        MockUtils.restore_mocks(mock_modules, original_modules)
        self.assertNotIn('test_mock_module', sys.modules)
