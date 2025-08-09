"""Library management route handlers for DazCAD server."""

from sanic.response import json as json_response

# Import dependencies with fallback for direct execution
try:
    from .server_core import run_cadquery_code, library_manager
    from .colored_logging import (log_server_call, log_input, log_output,
                                 log_error, log_success, log_debug)
except ImportError:
    # Fallback for direct execution
    from server_core import run_cadquery_code, library_manager
    from colored_logging import (log_server_call, log_input, log_output,
                                log_error, log_success, log_debug)


async def list_library_files(_request):
    """List all library files."""
    log_server_call("/library/list", "GET")

    try:
        log_debug("LIBRARY_LIST", "🔄 Starting library file listing process")
        log_debug("LIBRARY_LIST", f"Library manager type: {type(library_manager)}")
        log_debug("LIBRARY_LIST", f"Library manager available: {library_manager is not None}")

        files = library_manager.list_files()

        log_debug("LIBRARY_LIST", f"📁 Raw files from library_manager: {files}")
        log_debug("LIBRARY_LIST", f"📊 Files type: {type(files)}")

        if isinstance(files, dict):
            log_debug("LIBRARY_LIST", f"🔍 Files keys: {list(files.keys())}")
            for key, value in files.items():
                log_debug("LIBRARY_LIST", f"📋 {key}: {value} (type: {type(value)})")

        # Add debugging for the response structure
        response_data = {"success": True, "files": files}
        log_debug("LIBRARY_LIST", f"📤 Full response being sent: {response_data}")

        log_output("LIBRARY_LIST", files)
        return json_response(response_data)

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("LIBRARY_LIST", f"❌ Exception occurred: {error_msg}")
        import traceback  # pylint: disable=import-outside-toplevel
        traceback_str = traceback.format_exc()
        log_debug("LIBRARY_LIST", f"📍 Full traceback: {traceback_str}")
        return json_response({"success": False, "error": error_msg})


async def get_library_file(_request, file_type, n):
    """Get content of a library file."""
    log_server_call(f"/library/{file_type}/{n}", "GET")

    try:
        log_input("LIBRARY_GET", {"file_type": file_type, "filename": n})
        log_debug("LIBRARY_GET", f"🔍 Requesting file: {n} of type: {file_type}")

        # Add .py extension if not present
        filename = n if n.endswith('.py') else f"{n}.py"
        log_debug("LIBRARY_GET", f"📄 Full filename: {filename}")

        # The get_file_content method only takes filename, not file_type
        # It searches both built_in and user directories automatically
        content = library_manager.get_file_content(filename)

        if content is None:
            log_error("LIBRARY_GET", f"❌ File {filename} not found")
            return json_response({"success": False, "error": "File not found"}, status=404)

        log_success("LIBRARY_GET", f"✅ File {filename} found and loaded")
        log_output("LIBRARY_GET", {"success": True, "content_length": len(content)})
        return json_response({"success": True, "content": content})

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("LIBRARY_GET", f"❌ Exception: {error_msg}")
        import traceback  # pylint: disable=import-outside-toplevel
        traceback_str = traceback.format_exc()
        log_debug("LIBRARY_GET", f"📍 Full traceback: {traceback_str}")
        return json_response({"success": False, "error": error_msg})


async def save_library_file(request):
    """Save a library file."""
    log_server_call("/library/save", "POST")

    try:
        data = request.json
        name = data.get('name')
        content = data.get('content')
        old_name = data.get('old_name')
        file_type = data.get('type', 'user')

        log_input("LIBRARY_SAVE", {
            "name": name,
            "old_name": old_name,
            "type": file_type,
            "content_length": len(content) if content else 0
        })

        if not name or content is None:
            log_error("LIBRARY_SAVE", "Missing name or content")
            return json_response({"success": False, "error": "Missing name or content"},
                               status=400)

        # Create options dict for the new API
        options = {
            'old_name': old_name,
            'commit_message': f"Update {name}"
        }
        success, message = library_manager.save_file(name, content, file_type, options)

        # Also run the code to check if it's valid
        if success:
            result = run_cadquery_code(content)
            response_data = {
                "success": True,
                "message": message,
                "run_result": result
            }
            log_output("LIBRARY_SAVE", {"success": True, "message": message})
            return json_response(response_data)

        log_error("LIBRARY_SAVE", message)
        return json_response({"success": False, "error": message})

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("LIBRARY_SAVE", error_msg)
        return json_response({"success": False, "error": error_msg})


async def create_library_file(request):
    """Create a new library file."""
    log_server_call("/library/create", "POST")

    try:
        data = request.json
        name = data.get('name')

        log_input("LIBRARY_CREATE", {"name": name})

        if not name:
            log_error("LIBRARY_CREATE", "Missing name")
            return json_response({"success": False, "error": "Missing name"}, status=400)

        # Ensure the filename has .py extension
        if not name.endswith('.py'):
            filename = f"{name}.py"
        else:
            filename = name

        # Create default content template for new files
        default_content = '''"""Created with DazCAD - A parametric CAD model."""

import cadquery as cq


def create_model():
    """Create a parametric model."""
    return cq.Workplane("XY").box(20, 20, 10).edges("|Z").fillet(2)


# Create the model
model = create_model()
'''

        # The create_file method returns a dictionary, not a tuple
        result = library_manager.create_file(filename, default_content)
        
        success = result.get('success', False)
        message = result.get('message', 'Unknown error')

        if success:
            log_success("LIBRARY_CREATE", message)
        else:
            log_error("LIBRARY_CREATE", message)

        return json_response({"success": success, "message": message})

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("LIBRARY_CREATE", error_msg)
        return json_response({"success": False, "error": error_msg})
