"""Code execution route handlers for DazCAD server."""

import traceback
import unittest
from sanic.response import json as json_response

# Import dependencies with fallback for direct execution
try:
    from .server_core import run_cadquery_code
    from .colored_logging import (log_server_call, log_input, log_output,
                                 log_error)
except ImportError:
    # Fallback for direct execution
    from server_core import run_cadquery_code
    from colored_logging import (log_server_call, log_input, log_output,
                                log_error)


async def run_code(request):
    """Execute CadQuery code and return 3D data."""
    log_server_call("/run_code", "POST")

    try:
        code = request.json.get('code', '')
        log_input("CODE", code, max_length=100)

        if not code:
            log_error("RUN_CODE", "No code provided")
            return json_response({'error': 'No code provided'}, status=400)

        result = run_cadquery_code(code)

        # Log result summary (not full objects due to size)
        summary = {
            'success': result.get('success'),
            'objects_count': len(result.get('objects', [])),
            'has_output': bool(result.get('output')),
            'has_error': bool(result.get('error'))
        }
        log_output("RUN_CODE", summary)

        return json_response(result)

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("RUN_CODE", error_msg)
        traceback.print_exc()
        # Include traceback in server errors too
        error_traceback = traceback.format_exc()
        return json_response({
            'success': False,
            'error': error_msg,
            'traceback': error_traceback
        })


class TestCodeRoutes(unittest.TestCase):
    """Tests for code execution route handlers."""

    def test_run_code_function_exists(self):
        """Test that run_code function exists."""
        self.assertTrue(callable(run_code))
