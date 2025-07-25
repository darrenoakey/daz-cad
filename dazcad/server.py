"""Sanic server for DazCAD - a simple CadQuery runner."""

import base64
import os
import sys
import tempfile
import unittest
from io import StringIO

import cadquery as cq
from sanic import Sanic, response
from sanic.response import json as json_response


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


@app.route("/run", methods=["POST"])
async def run_code(request):
    """Execute CadQuery code and return 3D data."""
    # pylint: disable=global-statement
    global shown_objects
    shown_objects = []
    # pylint: enable=global-statement

    try:
        code = request.json.get('code', '')
        if not code:
            return json_response({'error': 'No code provided'}, status=400)

        # Prepare execution environment
        exec_globals = {
            'cq': cq,
            'show_object': show_object,
            '__name__': '__main__'
        }

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # pylint: disable=exec-used
            exec(code, exec_globals)
            # pylint: enable=exec-used
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        # Process shown objects
        result_objects = []

        for shown in shown_objects:
            obj = shown['object']

            # Skip if not a CadQuery object
            if not hasattr(obj, 'val') and not hasattr(obj, 'exportStl'):
                continue

            # Create temporary STL file
            with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Export to STL using CadQuery's built-in exporter
                if hasattr(obj, 'exportStl'):
                    obj.exportStl(tmp_path)
                else:
                    # For other CadQuery objects, try to export
                    cq.exporters.export(obj, tmp_path, exportType='STL')

                # Read STL file and encode to base64
                with open(tmp_path, 'rb') as f:
                    stl_data = base64.b64encode(f.read()).decode('utf-8')

                result_objects.append({
                    'name': shown['name'],
                    'color': shown['color'] or '#808080',
                    'stl': stl_data
                })

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return json_response({
            'success': True,
            'objects': result_objects,
            'output': output
        })

    # pylint: disable=broad-exception-caught
    except Exception as e:
        return json_response({
            'success': False,
            'error': str(e)
        })
    # pylint: enable=broad-exception-caught


class ServerTests(unittest.TestCase):
    """Tests for server functionality - see test_server.py for full test suite."""

    def test_module_imports(self):
        """Test that the module can be imported."""
        # This is a stub test - full tests are in test_server.py
        self.assertTrue(hasattr(sys.modules[__name__], 'app'))
        self.assertTrue(hasattr(sys.modules[__name__], 'show_object'))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
