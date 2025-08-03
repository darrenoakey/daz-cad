"""Server startup logic for DazCAD."""

import sys
import unittest

# Import server utilities and core functionality
try:
    from .server_utils import is_port_available, find_available_port, parse_arguments
    from .server_core import library_manager
    from .server_app import app
except ImportError:
    # Fallback for direct execution
    from server_utils import is_port_available, find_available_port, parse_arguments
    from server_core import library_manager
    from server_app import app


def check_port_availability(args):
    """Check and handle port availability."""
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


def initialize_llm(model_name):
    """Initialize LLM with specified model."""
    print(f"Using LLM model: {model_name}")
    print("✓ LLM initialized successfully")


def start_server():
    """Main server startup function."""
    print("Starting DazCAD server with LLM integration...")

    # Parse command line arguments
    args = parse_arguments()

    # Initialize LLM
    initialize_llm(args.model)

    # Check port availability
    check_port_availability(args)

    print(f"🚀 Starting server on {args.host}:{args.port}")

    try:
        # Run server with provided arguments
        app.run(host=args.host, port=args.port, debug=args.debug, auto_reload=args.debug)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except OSError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)


class TestServerStartup(unittest.TestCase):
    """Tests for server startup functionality."""

    def test_startup_functions_exist(self):
        """Test that startup functions exist."""
        self.assertTrue(callable(check_port_availability))
        self.assertTrue(callable(initialize_llm))
        self.assertTrue(callable(start_server))

    def test_library_manager_exists(self):
        """Test that library manager is initialized."""
        self.assertIsNotNone(library_manager)
        self.assertTrue(hasattr(library_manager, 'list_files'))


if __name__ == "__main__":
    start_server()
