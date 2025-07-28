"""Static file route handlers for DazCAD server."""

import unittest
from sanic import response


async def index(_request):
    """Serve the main page."""
    return await response.file('index.html')


async def style(_request):
    """Serve the CSS file."""
    return await response.file('style.css')


async def script(_request):
    """Serve the JavaScript file with cache-busting headers."""
    resp = await response.file('script.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def chat_script(_request):
    """Serve the Chat JavaScript file with cache-busting headers."""
    resp = await response.file('chat.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def viewer_script(_request):
    """Serve the Viewer JavaScript file with cache-busting headers."""
    resp = await response.file('viewer.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def editor_script(_request):
    """Serve the Editor JavaScript file with cache-busting headers."""
    resp = await response.file('editor.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def library_script(_request):
    """Serve the Library JavaScript file with cache-busting headers."""
    resp = await response.file('library.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def library_ui_script(_request):
    """Serve the Library UI JavaScript file with cache-busting headers."""
    resp = await response.file('library_ui.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def library_file_ops_script(_request):
    """Serve the Library File Ops JavaScript file with cache-busting headers."""
    resp = await response.file('library_file_ops.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def library_save_ops_script(_request):
    """Serve the library save operations JavaScript file"""
    resp = await response.file('library_save_ops.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


async def autosave_script(_request):
    """Serve the autosave JavaScript file with cache-busting headers."""
    resp = await response.file('autosave.js')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


class TestStaticRoutes(unittest.TestCase):
    """Tests for static route handlers."""

    def test_route_functions_exist(self):
        """Test that route functions exist."""
        self.assertTrue(callable(index))
        self.assertTrue(callable(style))
        self.assertTrue(callable(script))
        self.assertTrue(callable(chat_script))
        self.assertTrue(callable(viewer_script))
        self.assertTrue(callable(editor_script))
        self.assertTrue(callable(library_script))
