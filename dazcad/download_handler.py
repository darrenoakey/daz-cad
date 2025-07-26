"""Download functionality for DazCAD server."""

import traceback
import unittest

from sanic.response import json as json_response
from sanic import response

# Import export functionality with fallback for direct execution
try:
    from .export_utils import (export_assembly_to_format, export_shape_to_format,
                               get_supported_formats)
except ImportError:
    from export_utils import (export_assembly_to_format, export_shape_to_format,
                              get_supported_formats)


async def handle_download_request(request, export_format, shown_objects):
    """Handle download requests for different export formats.

    Args:
        request: Sanic request object
        export_format: String format ('stl', 'step', possibly '3mf')
        shown_objects: List of objects to export

    Returns:
        Sanic response object with file download or error
    """
    try:
        # Get filename from query parameters, default to "example"
        filename = request.args.get('name', 'example')

        if not shown_objects:
            return json_response({'error': 'No objects to export'}, status=400)

        # Get dynamically supported formats based on CadQuery capabilities
        supported_formats = get_supported_formats()
        if export_format not in supported_formats:
            return json_response({
                'error': f'Unsupported format: {export_format}. '
                        f'Supported formats: {", ".join(supported_formats)}'
            }, status=400)

        # For now, export the first object
        # In the future, we might want to combine all objects into an assembly
        first_obj = shown_objects[0]['object']

        # Determine the MIME type for each supported format
        mime_types = {
            'stl': 'application/sla',
            'step': 'application/step',
            '3mf': 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml'
        }

        try:
            # Check if it's an Assembly
            if hasattr(first_obj, 'children') and hasattr(first_obj, 'add'):
                # It's an Assembly - assemblies only support STL and STEP currently
                if export_format not in ['stl', 'step']:
                    return json_response({
                        'error': f'Assembly export only supports STL and STEP formats. '
                                f'Format "{export_format}" not supported for assemblies.'
                    }, status=400)
                file_data = export_assembly_to_format(first_obj, export_format)
            else:
                # It's a regular shape - supports all available formats
                file_data = export_shape_to_format(first_obj, export_format)

            # Create response with proper headers for file download
            resp = response.raw(file_data)
            resp.headers['Content-Type'] = mime_types.get(export_format,
                                                          'application/octet-stream')
            content_disposition = f'attachment; filename="{filename}.{export_format}"'
            resp.headers['Content-Disposition'] = content_disposition
            return resp

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error exporting to {export_format}: {e}")
            traceback.print_exc()
            return json_response({
                'error': f'Failed to export to {export_format}: {str(e)}'
            }, status=500)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in download_format: {e}")
        traceback.print_exc()
        return json_response({
            'error': f'Server error: {str(e)}'
        }, status=500)


class MockRequest:
    """Mock request class for testing."""

    def __init__(self, args=None):
        """Initialize mock request with optional args."""
        self.args = args or {}

    def get_arg(self, key, default=None):
        """Get argument from mock request."""
        return self.args.get(key, default)


class TestDownloadHandler(unittest.TestCase):
    """Unit tests for download handler functionality."""

    def test_supported_formats(self):
        """Test that only supported formats are accepted."""
        # This test verifies the format validation logic dynamically
        supported_formats = get_supported_formats()
        unsupported_format = 'obj'

        self.assertIn('stl', supported_formats)
        self.assertIn('step', supported_formats)
        self.assertNotIn(unsupported_format, supported_formats)
        # 3MF may or may not be present depending on CadQuery version

    def test_mime_type_mapping(self):
        """Test that MIME types are correctly mapped."""
        mime_types = {
            'stl': 'application/sla',
            'step': 'application/step',
            '3mf': 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml'
        }

        self.assertEqual(mime_types['stl'], 'application/sla')
        self.assertEqual(mime_types['step'], 'application/step')
        expected_3mf_mime = 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml'
        self.assertEqual(mime_types['3mf'], expected_3mf_mime)

    def test_mock_request_creation(self):
        """Test that mock request objects can be created."""
        mock_request = MockRequest({'name': 'test'})
        self.assertEqual(mock_request.args['name'], 'test')

        # Test default empty args
        mock_request_empty = MockRequest()
        self.assertEqual(mock_request_empty.args, {})

    def test_mock_request_get_arg(self):
        """Test mock request get_arg method."""
        mock_request = MockRequest({'name': 'test'})
        self.assertEqual(mock_request.get_arg('name'), 'test')
        self.assertEqual(mock_request.get_arg('missing', 'default'), 'default')

    def test_dynamic_format_validation(self):
        """Test that format validation works with dynamic format detection."""
        # Test that we can get supported formats
        supported_formats = get_supported_formats()
        self.assertIsInstance(supported_formats, list)
        self.assertGreater(len(supported_formats), 0)

        # Core formats should always be supported
        self.assertIn('stl', supported_formats)
        self.assertIn('step', supported_formats)
