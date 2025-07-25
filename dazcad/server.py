"""Sanic server for DazCAD - a simple CadQuery runner."""

import base64
import os
import sys
import tempfile
import traceback
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


def color_to_hex(color_tuple):
    """Convert Color tuple to hex string."""
    if color_tuple:
        # Color tuple is (r, g, b, a) with values 0-1
        r = int(color_tuple[0] * 255)
        g = int(color_tuple[1] * 255)
        b = int(color_tuple[2] * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    return "#808080"


def export_shape_to_stl(shape):
    """Export a shape to STL and return base64 encoded data."""
    with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Export to STL
        cq.exporters.export(shape, tmp_path, exportType='STL')

        # Read STL file and encode to base64
        with open(tmp_path, 'rb') as f:
            stl_data = base64.b64encode(f.read()).decode('utf-8')
        return stl_data

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def process_assembly(shown):
    """Process an Assembly object and return list of result objects."""
    results = []
    obj = shown['object']

    print(f"Processing assembly with {len(obj.children)} children")

    for i, child in enumerate(obj.children):
        print(f"Processing child {i}: {child.name}")

        # Get the shape with proper transformation applied
        transformed_shape = child.shape
        if child.loc:
            # Apply the location transformation
            transformed_shape = child.shape.moved(child.loc)

        # Wrap in CadQuery object for export
        cq_obj = cq.Workplane().add(transformed_shape)

        color_tuple = child.color.toTuple() if child.color else None
        part_color = color_to_hex(color_tuple)
        print(f"  Color: {part_color}")

        # pylint: disable=broad-exception-caught
        try:
            stl_data = export_shape_to_stl(cq_obj)

            results.append({
                'name': f"{shown['name']}_{child.name}",
                'color': part_color,
                'stl': stl_data
            })
            print(f"  Successfully exported {child.name}")
        except Exception as e:
            print(f"  Error exporting {child.name}: {e}")
        # pylint: enable=broad-exception-caught

    return results


def process_regular_object(shown):
    """Process a regular CadQuery object and return result object."""
    obj = shown['object']

    # Skip if not a CadQuery object
    if not hasattr(obj, 'val') and not hasattr(obj, 'exportStl'):
        return None

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

        return {
            'name': shown['name'],
            'color': shown['color'] or '#808080',
            'stl': stl_data
        }

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


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

        # Import Color and Assembly for exec environment
        # pylint: disable=import-outside-toplevel
        from cadquery import Color, Assembly
        # pylint: enable=import-outside-toplevel

        # Prepare execution environment
        exec_globals = {
            'cq': cq,
            'Color': Color,
            'Assembly': Assembly,
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

            # Check if it's an Assembly
            is_assembly = (hasattr(obj, '__class__') and
                          obj.__class__.__name__ == 'Assembly')

            if is_assembly:
                # Process assembly parts
                results = process_assembly(shown)
                result_objects.extend(results)
            else:
                # Process regular object
                result = process_regular_object(shown)
                if result:
                    result_objects.append(result)

        print(f"Total objects to return: {len(result_objects)}")

        return json_response({
            'success': True,
            'objects': result_objects,
            'output': output
        })

    # pylint: disable=broad-exception-caught
    except Exception as e:
        print(f"Error in run_code: {e}")
        traceback.print_exc()
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
    # Run in debug mode with auto-reload
    app.run(host="127.0.0.1", port=8000, debug=True, auto_reload=True)
