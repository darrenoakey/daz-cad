"""Main diagnostic script to identify DazCAD issues."""

# Import diagnostic functions from specialized modules
try:
    from .diagnostic_cadquery import test_cadquery_basic
    from .diagnostic_library import test_library_manager
    from .diagnostic_export import test_export_functionality
    from .diagnostic_execution import test_library_file_execution
except ImportError:
    # Fallback for direct execution
    from diagnostic_cadquery import test_cadquery_basic
    from diagnostic_library import test_library_manager
    from diagnostic_export import test_export_functionality
    from diagnostic_execution import test_library_file_execution


def run_diagnostics():
    """Run all diagnostics."""
    print("=== DazCAD Diagnostic Report ===\\n")

    print("1. Testing CadQuery basic functionality:")
    cadquery_ok = test_cadquery_basic()
    print()

    print("2. Testing Library Manager:")
    library_ok = test_library_manager()
    print()

    print("3. Testing Export functionality:")
    export_ok = test_export_functionality()
    print()

    print("4. Testing Library file execution:")
    execution_ok = test_library_file_execution()
    print()

    print("=== Summary ===")
    print(f"CadQuery basic: {'✓' if cadquery_ok else '✗'}")
    print(f"Library Manager: {'✓' if library_ok else '✗'}")
    print(f"Export functionality: {'✓' if export_ok else '✗'}")
    print(f"Library execution: {'✓' if execution_ok else '✗'}")

    if all([cadquery_ok, library_ok, export_ok, execution_ok]):
        print("\\n✓ All tests passed - DazCAD should work correctly")
    else:
        print("\\n✗ Some tests failed - this explains the reported issues")


if __name__ == "__main__":
    run_diagnostics()
