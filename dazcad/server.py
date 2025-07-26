"""Sanic server for DazCAD - a simple CadQuery runner with LLM integration."""

import argparse
import sys
import traceback
import unittest
from io import StringIO

import cadquery as cq
from sanic import Sanic, response
from sanic.response import json as json_response

# Import LLM chat functionality with fallback for direct execution
try:
    from .llm_chat import improve_code_with_llm, is_llm_available, set_llm_model
    from .cadquery_processor import process_objects
except ImportError:
    # Fallback for direct execution
    from llm_chat import improve_code_with_llm, is_llm_available, set_llm_model
    from cadquery_processor import process_objects

app = Sanic("dazcad")

# Store for objects shown via show_object
shown_objects = []


def show_object(obj, name=None, color=None):
    """Capture objects to be displayed."""
    shown_objects.append({
        'object': obj,
        'name': name or f'Object_{len(shown_objects)}',
        'color': color
    })
    return obj


@app.route("/")
async def index(_request):
    """Serve the main page."""
    return await response.file('index.html')


@app.route("/style.css")
async def style(_request):
    """Serve the CSS file."""
    return await response.file('style.css')


@app.route("/script.js")
async def script(_request):
    """Serve the JavaScript file."""
    return await response.file('script.js')


@app.route("/chat.js")
async def chat_script(_request):
    """Serve the Chat JavaScript file."""
    return await response.file('chat.js')


def run_cadquery_code(code_str):
    """Execute CadQuery code and capture results"""
    global shown_objects  # pylint: disable=global-statement
    shown_objects = []

    # Import everything needed for exec environment
    # pylint: disable=import-outside-toplevel
    from cadquery import Color, Assembly, Location, Workplane, Vector
    # pylint: enable=import-outside-toplevel

    # Prepare execution environment
    exec_globals = {
        'cq': cq,
        'Color': Color,
        'Assembly': Assembly,
        'Location': Location,
        'Workplane': Workplane,
        'Vector': Vector,
        'show_object': show_object,
        '__name__': '__main__'
    }

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # pylint: disable=exec-used
        exec(code_str, exec_globals)
        # pylint: enable=exec-used
        output = sys.stdout.getvalue()
    except Exception as e:  # pylint: disable=broad-exception-caught
        output = None
        error = str(e)
        return {"success": False, "error": error, "objects": []}
    finally:
        sys.stdout = old_stdout

    # Process shown objects
    result_objects = process_objects(shown_objects)

    return {"success": True, "objects": result_objects, "output": output}


@app.route("/run", methods=["POST"])
async def run_code(request):
    """Execute CadQuery code and return 3D data."""
    global shown_objects  # pylint: disable=global-statement
    shown_objects = []

    try:
        code = request.json.get('code', '')
        if not code:
            return json_response({'error': 'No code provided'}, status=400)

        result = run_cadquery_code(code)
        return json_response(result)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in run_code: {e}")
        traceback.print_exc()
        return json_response({
            'success': False,
            'error': str(e)
        })


@app.route("/chat", methods=["POST"])
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


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='DazCAD Server with LLM integration')
    parser.add_argument(
        '--model',
        type=str,
        default='ollama:mixtral8:7b',
        help='LLM model to use (default: ollama:mixtral8:7b)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind to (default: 8000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (default: False)'
    )
    return parser.parse_args()


class ServerTests(unittest.TestCase):
    """Tests for server functionality - see test_server.py for full test suite."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        # This is a stub test - full tests are in test_server.py
        self.assertTrue(hasattr(sys.modules[__name__], 'app'))
        self.assertTrue(hasattr(sys.modules[__name__], 'show_object'))

    def test_parse_arguments_default(self):
        """Test argument parsing with defaults"""
        # Save original sys.argv
        original_argv = sys.argv
        try:
            # Test with no arguments
            sys.argv = ['server.py']
            parsed_args = parse_arguments()
            self.assertEqual(parsed_args.model, 'ollama:mixtral8:7b')
            self.assertEqual(parsed_args.host, '127.0.0.1')
            self.assertEqual(parsed_args.port, 8000)
            self.assertFalse(parsed_args.debug)
        finally:
            # Restore original sys.argv
            sys.argv = original_argv


if __name__ == "__main__":
    print("Starting DazCAD server with LLM integration...")

    # Parse command line arguments
    args = parse_arguments()

    # Set the LLM model from command line
    print(f"Using LLM model: {args.model}")
    set_llm_model(args.model)

    # Test LLM initialization
    if is_llm_available():
        print("✓ LLM initialized successfully")
    else:
        print("⚠ LLM not available - chat features disabled")

    # Run server with provided arguments
    app.run(host=args.host, port=args.port, debug=args.debug, auto_reload=args.debug)
