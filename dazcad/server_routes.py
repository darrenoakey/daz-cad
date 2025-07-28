"""Sanic route handlers for DazCAD server."""

import traceback
import unittest
from sanic.response import json as json_response

# Import dependencies with fallback for direct execution
try:
    from .llm_chat import improve_code_with_llm
    from .download_handler import handle_download_request
    from .server_core import run_cadquery_code, library_manager, shown_objects
except ImportError:
    # Fallback for direct execution
    from llm_chat import improve_code_with_llm
    from download_handler import handle_download_request
    from server_core import run_cadquery_code, library_manager, shown_objects


async def run_code(request):
    """Execute CadQuery code and return 3D data."""
    try:
        code = request.json.get('code', '')
        if not code:
            return json_response({'error': 'No code provided'}, status=400)

        result = run_cadquery_code(code)
        return json_response(result)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in run_code: {e}")
        traceback.print_exc()
        # Include traceback in server errors too
        error_traceback = traceback.format_exc()
        return json_response({
            'success': False,
            'error': str(e),
            'traceback': error_traceback
        })


async def download_format(request, export_format):
    """Download the current assembly in the specified format."""
    try:
        # Check if there are any objects to export
        if not shown_objects:
            error_msg = ('No objects to export. Please run some CadQuery code '
                        'first to generate objects.')
            return json_response({'error': error_msg}, status=400)

        return await handle_download_request(request, export_format, shown_objects)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in download_format: {e}")
        traceback.print_exc()
        return json_response({
            'error': f'Download error: {str(e)}'
        }, status=500)


async def chat_with_ai(request):
    """Handle AI chat requests for code improvement"""
    try:
        user_message = request.json.get('message', '')
        current_code = request.json.get('code', '')

        # Use the LLM chat module
        result = improve_code_with_llm(user_message, current_code, run_cadquery_code)
        return json_response(result)

    except Exception as e:  # pylint: disable=broad-exception-caught
        return json_response({
            "success": False,
            "error": f"Server error: {str(e)}",
            "response": "Sorry, I encountered an error while processing your request."
        })


async def list_library_files(_request):
    """List all library files."""
    try:
        files = library_manager.list_files()
        return json_response({"success": True, "files": files})
    except Exception as e:  # pylint: disable=broad-exception-caught
        return json_response({"success": False, "error": str(e)})


async def get_library_file(_request, file_type, n):
    """Get content of a library file."""
    try:
        content = library_manager.get_file_content(n, file_type)
        if content is None:
            return json_response({"success": False, "error": "File not found"}, status=404)
        return json_response({"success": True, "content": content})
    except Exception as e:  # pylint: disable=broad-exception-caught
        return json_response({"success": False, "error": str(e)})


async def save_library_file(request):
    """Save a library file."""
    try:
        data = request.json
        name = data.get('name')
        content = data.get('content')
        old_name = data.get('old_name')
        file_type = data.get('type', 'user')

        if not name or content is None:
            return json_response({"success": False, "error": "Missing name or content"},
                               status=400)

        success, message = library_manager.save_file(name, content, old_name, file_type)

        # Also run the code to check if it's valid
        if success:
            result = run_cadquery_code(content)
            return json_response({
                "success": True,
                "message": message,
                "run_result": result
            })

        return json_response({"success": False, "error": message})

    except Exception as e:  # pylint: disable=broad-exception-caught
        return json_response({"success": False, "error": str(e)})


async def create_library_file(request):
    """Create a new library file."""
    try:
        data = request.json
        name = data.get('name')

        if not name:
            return json_response({"success": False, "error": "Missing name"}, status=400)

        success, message = library_manager.create_file(name)
        return json_response({"success": success, "message": message})

    except Exception as e:  # pylint: disable=broad-exception-caught
        return json_response({"success": False, "error": str(e)})


class TestRoutes(unittest.TestCase):
    """Tests for route handlers."""

    def test_route_functions_exist(self):
        """Test that route functions exist."""
        self.assertTrue(callable(run_code))
        self.assertTrue(callable(list_library_files))
        self.assertTrue(callable(get_library_file))

    def test_library_manager_access(self):
        """Test that library manager is accessible."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))
