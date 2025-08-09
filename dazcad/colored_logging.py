"""Colored logging utilities for DazCAD server."""

import json
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init(autoreset=True)  # Automatically reset colors after each print
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback - no colors
    class FallbackColor:
        """Fallback color class when colorama not available."""
        def __getattr__(self, name):
            """Return empty string for any color attribute."""
            return ""

        def __repr__(self):
            """String representation of FallbackColor."""
            return "FallbackColor()"

    Fore = FallbackColor()
    Style = FallbackColor()


def log_server_call(endpoint, method="GET"):
    """Log a server endpoint call."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if COLORAMA_AVAILABLE:
        print(f"{Fore.CYAN}[{timestamp}] 🌐 SERVER CALL: {method} {endpoint}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] SERVER CALL: {method} {endpoint}")


def log_input(label, data, max_length=200):
    """Log input data with truncation."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    # Format data for display
    if isinstance(data, dict):
        display_data = json.dumps(data, indent=None, separators=(',', ':'))
    elif isinstance(data, str):
        display_data = data
    else:
        display_data = str(data)

    # Truncate if too long
    if len(display_data) > max_length:
        display_data = display_data[:max_length] + "..."

    if COLORAMA_AVAILABLE:
        print(f"{Fore.GREEN}[{timestamp}] 📥 INPUT {label}: {display_data}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] INPUT {label}: {display_data}")


def log_output(label, data, max_length=200):
    """Log output data with truncation."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    # Format data for display
    if isinstance(data, dict):
        display_data = json.dumps(data, indent=None, separators=(',', ':'))
    elif isinstance(data, str):
        display_data = data
    else:
        display_data = str(data)

    # Truncate if too long
    if len(display_data) > max_length:
        display_data = display_data[:max_length] + "..."

    if COLORAMA_AVAILABLE:
        print(f"{Fore.YELLOW}[{timestamp}] 📤 OUTPUT {label}: {display_data}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] OUTPUT {label}: {display_data}")


def log_error(label, error_msg):
    """Log error messages."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    if COLORAMA_AVAILABLE:
        print(f"{Fore.RED}[{timestamp}] ❌ ERROR {label}: {error_msg}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] ERROR {label}: {error_msg}")


def log_success(label, message):
    """Log success messages."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    if COLORAMA_AVAILABLE:
        print(f"{Fore.GREEN}[{timestamp}] ✅ SUCCESS {label}: {message}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] SUCCESS {label}: {message}")


def log_debug(label, message):
    """Log debug information."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    if COLORAMA_AVAILABLE:
        print(f"{Fore.MAGENTA}[{timestamp}] 🔍 DEBUG {label}: {message}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] DEBUG {label}: {message}")


def log_library_operation(operation, details):
    """Log library-related operations."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    if COLORAMA_AVAILABLE:
        print(f"{Fore.BLUE}[{timestamp}] 📚 LIBRARY {operation}: {details}{Style.RESET_ALL}")
    else:
        print(f"[{timestamp}] LIBRARY {operation}: {details}")
