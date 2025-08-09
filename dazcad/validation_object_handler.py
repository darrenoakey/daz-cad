"""Object validation handler for CadQuery library files."""

try:
    from .test_cadquery_file import test_export_format
    from .library_validation_core import validate_cadquery_object
except ImportError:
    # Fallback for direct execution
    from test_cadquery_file import test_export_format
    from library_validation_core import validate_cadquery_object


def validate_single_object(obj_info, supported_formats, verbose):
    """Validate a single object and test its exports.

    Args:
        obj_info: Dictionary with object information
        supported_formats: List of supported export formats
        verbose: Whether to print verbose output

    Returns:
        Tuple of (obj_result dict, export_test_count, successful_export_count)
    """
    obj = obj_info['object']
    obj_name = obj_info['name']
    obj_type = obj_info['type']

    # Validate object structure
    obj_valid, obj_error = validate_cadquery_object(obj)
    obj_result = {
        'name': obj_name,
        'type': obj_type,
        'valid': obj_valid,
        'error': obj_error,
        'exports': {}
    }

    export_test_count = 0
    successful_export_count = 0

    if obj_valid:
        # Test exports for valid objects
        for export_format in supported_formats:
            format_name = export_format.extension

            # Skip formats that don't support assemblies
            if (obj_type == 'assembly' and
                export_format.assembly_handler is None):
                continue

            export_test_count += 1

            export_success, export_error = test_export_format(
                obj, obj_type, format_name)

            obj_result['exports'][format_name] = {
                'success': export_success,
                'error': export_error
            }

            if export_success:
                successful_export_count += 1
            elif verbose:
                print(f"  ❌ {obj_name} -> {format_name}: {export_error}")
    elif verbose:
        print(f"  ❌ {obj_name}: Invalid object - {obj_error}")

    return obj_result, export_test_count, successful_export_count
