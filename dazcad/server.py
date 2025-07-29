"""Sanic server for DazCAD - main entry point and route registration."""

import argparse
import sys
import unittest

from sanic import Sanic

# Import LLM chat functionality with fallback for direct execution
try:
    from .llm_chat import is_llm_available, set_llm_model
    from .server_static_routes import (
        index, style, script, chat_script, viewer_script, editor_script,
        library_script, library_ui_script, library_file_ops_script,
        library_save_ops_script, autosave_script
    )
    from .server_routes import (
        run_code, download_format, chat_with_ai, list_library_files,
        get_library_file, save_library_file, create_library_file
    )
    from .server_core import library_manager
except ImportError:
    # Fallback for direct execution
    from llm_chat import is_llm_available, set_llm_model
    from server_static_routes import (
        index, style, script, chat_script, viewer_script, editor_script,
        library_script, library_ui_script, library_file_ops_script,
        library_save_ops_script, autosave_script
    )
    from server_routes import (
        run_code, download_format, chat_with_ai, list_library_files,
        get_library_file, save_library_file, create_library_file
    )
    from server_core import library_manager

app = Sanic("dazcad")

# Register static file routes
app.route("/")(index)
app.route("/style.css")(style)
app.route("/script.js")(script)
app.route("/chat.js")(chat_script)
app.route("/viewer.js")(viewer_script)
app.route("/editor.js")(editor_script)
app.route("/library.js")(library_script)
app.route("/library_ui.js")(library_ui_script)
app.route("/autosave.js")(autosave_script)
app.route("/library_file_ops.js")(library_file_ops_script)
app.route("/library_save_ops.js")(library_save_ops_script)

# Register API routes
app.route("/run", methods=["POST"])(run_code)
app.route("/download/<export_format>", methods=["GET", "POST"])(download_format)
app.route("/chat", methods=["POST"])(chat_with_ai)

# Register library routes
app.route("/library/list", methods=["GET"])(list_library_files)
app.route("/library/get/<file_type>/<n>", methods=["GET"])(get_library_file)
app.route("/library/save", methods=["POST"])(save_library_file)
app.route("/library/create", methods=["POST"])(create_library_file)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='DazCAD Server with LLM integration')
    parser.add_argument(
        '--model',
        type=str,
        default='ollama:mixtral:8x7b',
        help='LLM model to use (default: ollama:mixtral:8x7b)'
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
        self.assertIsNotNone(app)

    def test_parse_arguments_default(self):
        """Test argument parsing with defaults"""
        # Save original sys.argv
        original_argv = sys.argv
        try:
            # Test with no arguments
            sys.argv = ['server.py']
            parsed_args = parse_arguments()
            self.assertEqual(parsed_args.model, 'ollama:mixtral:8x7b')
            self.assertEqual(parsed_args.host, '127.0.0.1')
            self.assertEqual(parsed_args.port, 8000)
            self.assertFalse(parsed_args.debug)
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def test_library_manager_exists(self):
        """Test that library manager is initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))


if __name__ == "__main__":
    print("Starting DazCAD server with LLM integration...")

    # Parse command line arguments
    args = parse_arguments()

    # Set the LLM model from command line
    print(f"Using LLM model: {args.model}")
    set_llm_model(args.model)

    # Test LLM initialization - fail hard if not available
    llm_available = is_llm_available()
    if not llm_available:
        raise RuntimeError("LLM not available - cannot start server without valid LLM model")

    print("✓ LLM initialized successfully")

    # Run server with provided arguments
    app.run(host=args.host, port=args.port, debug=args.debug, auto_reload=args.debug)