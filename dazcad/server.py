"""Sanic server for DazCAD - a simple CadQuery runner."""

import base64
import sys
import tempfile
import unittest
from io import StringIO

import cadquery as cq
from sanic import Sanic, response
from sanic.response import json as json_response

# These imports may show as errors in pylint but are correct for CadQuery
# pylint: disable=no-name-in-module
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Shape
# pylint: enable=no-name-in-module


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

            # Convert to STL
            if hasattr(obj, 'val'):
                shape = obj.val()
            elif isinstance(obj, TopoDS_Shape):
                shape = obj
            else:
                continue

            # Generate mesh
            mesh = BRepMesh_IncrementalMesh(shape, 0.1)
            mesh.Perform()

            # Write STL to bytes
            with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
                writer = StlAPI_Writer()
                writer.Write(shape, tmp.name)
                tmp.seek(0)
                with open(tmp.name, 'rb') as f:
                    stl_data = base64.b64encode(f.read()).decode('utf-8')

            result_objects.append({
                'name': shown['name'],
                'color': shown['color'] or '#808080',
                'stl': stl_data
            })

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
