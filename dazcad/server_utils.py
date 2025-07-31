"""Server utility functions for DazCAD."""

import argparse
import socket
import unittest


def is_port_available(host, port):
    """Check if a port is available on the given host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0
    except socket.error:
        return False


def find_available_port(host, start_port, max_port=9000):
    """Find an available port starting from start_port."""
    for port in range(start_port, max_port + 1):
        if is_port_available(host, port):
            return port
    return None


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
    parser.add_argument(
        '--auto-port',
        action='store_true',
        help='Automatically find an available port if the specified port is in use'
    )
    return parser.parse_args()


class TestServerUtilsBasic(unittest.TestCase):
    """Basic tests for server utilities."""

    def test_module_functions_exist(self):
        """Test that module functions exist."""
        self.assertTrue(callable(is_port_available))
        self.assertTrue(callable(find_available_port))
        self.assertTrue(callable(parse_arguments))
