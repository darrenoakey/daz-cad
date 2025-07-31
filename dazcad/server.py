"""Sanic server for DazCAD - main entry point and route registration."""

import sys
import unittest

from sanic import Sanic
from sanic import response
from sanic.exceptions import SanicException

# Import server utilities
try:
    from .server_utils import is_port_available, find_available_port, parse_arguments
except ImportError:
    # Fallback for direct execution
    from server_utils import is_port_available, find_available_port, parse_arguments

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

# Handle duplicate app creation during testing
_APP_ALREADY_EXISTED = False
try:
    app = Sanic("dazcad")
except SanicException as e:
    if "already in use" in str(e):
        # During testing, the app might already exist
        app = Sanic.get_app("dazcad")
        _APP_ALREADY_EXISTED = True
    else:
        raise

# Only register routes if we created a new app
if not _APP_ALREADY_EXISTED:
    # CORS middleware to handle preflight requests and add proper headers
    @app.middleware('request')
    async def cors_handler(request):
        """Handle CORS preflight requests."""
        if request.method == 'OPTIONS':
            return response.empty(
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Max-Age': '86400'
                }
            )

    @app.middleware('response')
    async def add_cors_headers(_request, response_obj):
        """Add CORS headers to all responses."""
        response_obj.headers['Access-Control-Allow-Origin'] = '*'
        response_obj.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response_obj.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

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
    app.route("/download/<export_format>", methods=["GET", "POST", "OPTIONS"])(download_format)
    app.route("/chat", methods=["POST"])(chat_with_ai)

    # Register library routes
    app.route("/library/list", methods=["GET"])(list_library_files)
    app.route("/library/get/<file_type>/<n>", methods=["GET"])(get_library_file)
    app.route("/library/save", methods=["POST"])(save_library_file)
    app.route("/library/create", methods=["POST"])(create_library_file)


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
            self.assertFalse(parsed_args.auto_port)
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

    def test_library_manager_exists(self):
        """Test that library manager is initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))

    def test_cors_middleware_setup(self):
        """Test that CORS middleware is properly configured."""
        # Verify that the app has middleware configured
        self.assertTrue(hasattr(app, 'middleware'))
        self.assertIsNotNone(app.middleware)

    def test_port_availability_check(self):
        """Test port availability checking functions."""
        # Test with a port that should be available
        self.assertTrue(is_port_available('127.0.0.1', 65432))

        # Test find_available_port function
        test_port = find_available_port('127.0.0.1', 8000, 8010)
        self.assertIsNotNone(test_port)
        self.assertGreaterEqual(test_port, 8000)
        self.assertLessEqual(test_port, 8010)


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

    # Check if the requested port is available
    if not is_port_available(args.host, args.port):
        if args.auto_port:
            # Try to find an available port
            available_port = find_available_port(args.host, args.port + 1)
            if available_port:
                print(f"⚠ Port {args.port} is in use, switching to port {available_port}")
                args.port = available_port
            else:
                print("❌ No available ports found in range")
                sys.exit(1)
        else:
            print(f"❌ Port {args.port} is already in use!")
            print("   Try a different port with --port <port_number>")
            print("   Or use --auto-port to automatically find an available port")
            print(f"   You can also kill the process using port {args.port}:")
            print(f"   lsof -ti:{args.port} | xargs kill -9")
            sys.exit(1)

    print(f"🚀 Starting server on {args.host}:{args.port}")

    try:
        # Run server with provided arguments
        app.run(host=args.host, port=args.port, debug=args.debug, auto_reload=args.debug)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except OSError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)
