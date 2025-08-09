"""Chat/AI route handlers for DazCAD server."""

from sanic.response import json as json_response

# Import dependencies with fallback for direct execution
try:
    from .llm import improve_code_with_llm
    from .server_core import run_cadquery_code
    from .colored_logging import (log_server_call, log_input, log_output,
                                 log_error)
except ImportError:
    # Fallback for direct execution
    from llm import improve_code_with_llm
    from server_core import run_cadquery_code
    from colored_logging import (log_server_call, log_input, log_output,
                                log_error)


async def chat_with_ai(request):
    """Handle AI chat requests for code improvement"""
    log_server_call("/chat", "POST")

    try:
        user_message = request.json.get('message', '')
        current_code = request.json.get('code', '')

        log_input("CHAT_MESSAGE", user_message)
        log_input("CHAT_CODE", current_code, max_length=100)

        # Use the LLM chat module
        result = improve_code_with_llm(user_message, current_code, run_cadquery_code)

        log_output("CHAT", {"success": result.get("success"),
                           "has_response": bool(result.get("response"))})
        return json_response(result)

    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = str(e)
        log_error("CHAT", error_msg)
        return json_response({
            "success": False,
            "error": f"Server error: {error_msg}",
            "response": "Sorry, I encountered an error while processing your request."
        })
