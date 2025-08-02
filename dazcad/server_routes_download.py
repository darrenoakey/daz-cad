"""Download route handlers for DazCAD server."""

import traceback
import unittest
from sanic.response import json as json_response
from sanic import response

# Import dependencies with fallback for direct execution
try:
    from .download_handler import handle_download_request
    from .server_core import run_cadquery_code, shown_objects
    from .colored_logging import (log_server_call, log_input,
                                 log_error, log_success, log_debug)
except ImportError:
    # Fallback for direct execution
    from download_handler import handle_download_request
    from server_core import run_cadquery_code, shown_objects
    from colored_logging import (log_server_call, log_input,
                                log_error, log_success, log_debug)


async def download_format(request, export_format):
    """Download the current assembly in the specified format."""
    log_server_call(f"/download/{export_format}", request.method)

    try:
        # Debug logging
        log_debug("DOWNLOAD", f"Request method: {request.method}, format: {export_format}")
        log_debug("DOWNLOAD", f"Headers: {dict(request.headers)}")

        # Handle OPTIONS requests for CORS preflight
        if request.method == 'OPTIONS':
            log_debug("DOWNLOAD", "Handling OPTIONS (preflight) request")
            return response.empty(
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Max-Age': '86400'
                }
            )

        # Handle POST requests that include code
        if request.method == 'POST':
            log_debug("DOWNLOAD", "Handling POST request")
            request_data = request.json
            code = request_data.get('code', '')

            # If code is provided, run it first
            if code:
                log_input("DOWNLOAD_CODE", code, max_length=100)
                result = run_cadquery_code(code)
                if not result.get('success'):
                    error_msg = (f"Failed to generate objects: "
                                f"{result.get('error', 'Unknown error')}")
                    log_error("DOWNLOAD", error_msg)
                    return json_response({'error': error_msg}, status=400)
                objects_count = len(result.get('objects', []))
                log_success("DOWNLOAD",
                           f"Code execution successful, {objects_count} objects generated")
            else:
                log_debug("DOWNLOAD", "No code provided in POST request")

        # Check if there are any objects to export
        if not shown_objects:
            error_msg = ('No objects to export. Please run some CadQuery code '
                        'first to generate objects.')
            log_error("DOWNLOAD", error_msg)
            return json_response({'error': error_msg}, status=400)

        log_debug("DOWNLOAD", f"Proceeding with download: {len(shown_objects)} objects available")
        return await handle_download_request(request, export_format, shown_objects)

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("DOWNLOAD", error_msg)
        traceback.print_exc()
        return json_response({
            'error': f'Download error: {error_msg}'
        }, status=500)


class TestDownloadRoutes(unittest.TestCase):
    """Tests for download route handlers."""

    def test_download_format_function_exists(self):
        """Test that download_format function exists."""
        self.assertTrue(callable(download_format))
