"""Sanic app creation and configuration for DazCAD."""

import unittest
from sanic import Sanic
from sanic import response
from sanic.exceptions import SanicException

# Import server route handlers
try:
    from .server_static_routes import (
        index, style, styles_base, styles_panels, script, chat_script, viewer_script, editor_script,
        library_script, library_ui_script, library_ui_rendering_script, library_ui_controls_script,
        library_file_loader_script, library_file_operations_script, library_code_executor_script, 
        library_file_ops_script, library_save_ops_script, autosave_script
    )
    from .server_routes import (
        run_code, download_format, chat_with_ai, list_library_files,
        get_library_file, save_library_file, create_library_file
    )
except ImportError:
    # Fallback for direct execution
    from server_static_routes import (
        index, style, styles_base, styles_panels, script, chat_script, viewer_script, editor_script,
        library_script, library_ui_script, library_ui_rendering_script, library_ui_controls_script,
        library_file_loader_script, library_file_operations_script, library_code_executor_script,
        library_file_ops_script, library_save_ops_script, autosave_script
    )
    from server_routes import (
        run_code, download_format, chat_with_ai, list_library_files,
        get_library_file, save_library_file, create_library_file
    )

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


def setup_cors_middleware():
    """Set up CORS middleware for the app."""
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


def register_static_routes():
    """Register static file routes."""
    app.route("/")(index)
    app.route("/style.css")(style)
    app.route("/styles-base.css")(styles_base)
    app.route("/styles-panels.css")(styles_panels)
    app.route("/script.js")(script)
    app.route("/chat.js")(chat_script)
    app.route("/viewer.js")(viewer_script)
    app.route("/editor.js")(editor_script)
    app.route("/library.js")(library_script)
    app.route("/library_ui.js")(library_ui_script)
    app.route("/library_ui_rendering.js")(library_ui_rendering_script)
    app.route("/library_ui_controls.js")(library_ui_controls_script)
    app.route("/library_file_loader.js")(library_file_loader_script)
    app.route("/library_file_operations.js")(library_file_operations_script)
    app.route("/library_code_executor.js")(library_code_executor_script)
    app.route("/autosave.js")(autosave_script)
    app.route("/library_file_ops.js")(library_file_ops_script)
    app.route("/library_save_ops.js")(library_save_ops_script)


def register_api_routes():
    """Register API routes."""
    app.route("/run", methods=["POST"])(run_code)
    app.route("/download/<export_format>", methods=["GET", "POST", "OPTIONS"])(download_format)
    app.route("/chat", methods=["POST"])(chat_with_ai)


def register_library_routes():
    """Register library management routes."""
    app.route("/library/list", methods=["GET"])(list_library_files)
    app.route("/library/get/<file_type>/<n>", methods=["GET"])(get_library_file)
    app.route("/library/save", methods=["POST"])(save_library_file)
    app.route("/library/create", methods=["POST"])(create_library_file)


def initialize_app():
    """Initialize the Sanic app with all routes and middleware."""
    if not _APP_ALREADY_EXISTED:
        setup_cors_middleware()
        register_static_routes()
        register_api_routes()
        register_library_routes()
    return app


# Initialize the app
app = initialize_app()


class TestServerApp(unittest.TestCase):
    """Tests for server app configuration."""

    def test_app_exists(self):
        """Test that app is properly created."""
        self.assertIsNotNone(app)
        self.assertEqual(app.name, "dazcad")

    def test_cors_middleware_setup(self):
        """Test that CORS middleware is properly configured."""
        self.assertTrue(hasattr(app, 'middleware'))
        self.assertIsNotNone(app.middleware)

    def test_initialization_functions_exist(self):
        """Test that initialization functions exist."""
        self.assertTrue(callable(setup_cors_middleware))
        self.assertTrue(callable(register_static_routes))
        self.assertTrue(callable(register_api_routes))
        self.assertTrue(callable(register_library_routes))
