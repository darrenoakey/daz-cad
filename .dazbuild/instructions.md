# Dazbuild Instructions

## DazCAD Repository Navigation Guide

### Project Overview
DazCAD is a web-based CadQuery development environment for 3D modeling and printing. The project has grown into multiple logical layers:

**Backend (Python)**: CadQuery processing, server infrastructure, library management
**Frontend (JavaScript)**: Web interface, 3D visualization, user interactions  
**Library (Python)**: Parametric CAD model examples and components
**Tests & Config**: Unit tests, linting rules, dependencies

### Directory Structure & Key Files

#### **Entry Points & Core Infrastructure**
- **`dazcad/server.py`** - Main application entry point, runs the web server
- **`dazcad/server_core.py`** - Core server functionality and Sanic app setup
- **`dazcad/server_routes.py`** - HTTP route handlers and API endpoints
- **`dazcad/index.html`** - Main web application interface

#### **Backend Processing Layer**
- **`dazcad/cadquery_processor.py`** - Core CadQuery code execution and object processing
- **`dazcad/cadquery_core.py`** - Low-level CadQuery operations and geometry handling
- **`dazcad/assembly_processor.py`** - Handles CadQuery assemblies with multiple parts
- **`dazcad/color_processor.py`** - Manages colors and materials for 3D objects
- **`dazcad/export_utils.py`** - STL/STEP/3MF file export functionality
- **`dazcad/download_handler.py`** - File download processing and response handling

#### **Library Management System**
- **`dazcad/library_manager.py`** - Complete library management including core operations (load, save, list) and coordination
- **`dazcad/library_manager_git.py`** - Git integration for library versioning
- **`dazcad/library/`** - Directory containing example CAD models:
  - `assembly.py` - Interlocking parametric parts
  - `bearing.py` - Mechanical bearing components
  - `bracket.py` - Mounting brackets and supports
  - `gear.py` - Parametric gear generation
  - `vase.py` - Decorative 3D printable objects

#### **Frontend JavaScript Layer**
- **`dazcad/script.js`** - Main frontend application logic
- **`dazcad/editor.js`** - Code editor functionality and Monaco integration
- **`dazcad/viewer.js`** - Three.js 3D visualization and rendering
- **`dazcad/viewer_utils.js`** - 3D viewer utilities and coordinate transformations
- **`dazcad/library.js`** - Library browser and example loading
- **`dazcad/library_ui.js`** - Library interface components and interactions
- **`dazcad/library_file_ops.js`** - File operations for library management
- **`dazcad/chat.js`** - LLM chat integration for code assistance
- **`dazcad/style.css`** - Application styling and layout

#### **LLM Integration**
- **`dazcad/llm_chat.py`** - Backend chat API and LLM communication
- **`dazcad/llm_core.py`** - Core LLM processing and response handling

#### **Testing & Configuration**
- **`dazcad/*_test.py`** - Unit tests for corresponding modules
- **`dazcad/.pylintrc`** - Code quality rules and linting configuration
- **`dazcad/requirements.txt`** - Python dependencies
- **`dazcad/README.md`** - User documentation and setup instructions

### Navigation Patterns for Common Tasks

#### **Adding New CAD Library Examples**
1. Create new `.py` file in `dazcad/library/`
2. Follow pattern from existing examples (assembly.py, gear.py, etc.)
3. Include unittest.TestCase with real tests
4. Ensure 3D printing readiness (parts on z=0 plane)

#### **Modifying 3D Visualization**
- **Frontend display issues**: Edit `viewer.js`, `viewer_utils.js`, or `style.css`
- **Backend data format**: Only touch if the core CadQuery output needs changes
- **Coordinate transformations**: Handle in `viewer_utils.js` frontend conversion functions

#### **Server & API Changes**
- **New routes**: Add to `server_routes.py`
- **Core server logic**: Modify `server_core.py`
- **Request processing**: Update relevant `*_processor.py` files

#### **Library Management Features**
- **Library UI**: Edit `library_ui.js` and `library.js`
- **Backend operations**: Modify `library_manager*.py` files
- **File operations**: Update `library_file_ops.js`

#### **Code Editor Enhancements**
- **Editor behavior**: Modify `editor.js`
- **Chat integration**: Update `chat.js` and `llm_*.py` files
- **Main app coordination**: Edit `script.js`

### Finding the Right File for Your Change

#### **"Where do I add...?"**
- **New CadQuery example** → `dazcad/library/[name].py`
- **New API endpoint** → `dazcad/server_routes.py`
- **Frontend UI change** → `dazcad/[component].js` + `style.css`
- **3D rendering fix** → `dazcad/viewer.js` or `viewer_utils.js`
- **Export format** → `dazcad/export_utils.py`
- **Code processing** → `dazcad/cadquery_processor.py`

#### **"Where is the bug in...?"**
- **3D display problems** → Check `viewer.js`, then `viewer_utils.js`
- **Code execution errors** → Look in `cadquery_processor.py` or `cadquery_core.py`
- **File downloads** → Check `download_handler.py` and export chain
- **Library loading** → Examine `library_manager*.py` and `library.js`
- **Server errors** → Start with `server_routes.py`, then `server_core.py`

### Workflow Best Practices

#### **Before Making Changes**
1. **`dazbuild_outline [file]`** - Understand the structure
2. **`dazbuild_get [file]`** - Examine current implementation
3. Identify the **smallest scope** for your change (function, method, class)

#### **During Development**
- **Edit minimal scope**: `file.py::ClassName::method_name` not entire files
- **Run tests often**: Use `dazbuild_end_change` to validate as you go
- **Follow naming patterns**: Match existing file naming conventions
- **Maintain separation**: Keep backend/frontend concerns separate

#### **Architecture Awareness**
- **Backend purity**: Never modify Python to fix display issues
- **Frontend adaptation**: Convert backend data to display requirements
- **Library standards**: New examples should be 3D print ready
- **Testing requirements**: Every Python file needs unittest.TestCase

### Quick Reference Commands

**Start working**: `dazbuild_start_change dazcad`
**See structure**: `dazbuild_outline dazcad [file]` 
**Read code**: `dazbuild_get dazcad [file]`
**Edit scope**: `dazbuild_write dazcad [file::class::method] [content]`
**Add component**: `dazbuild_add dazcad [type] [parent] [name] [content]`
**Finish & test**: `dazbuild_end_change dazcad "[commit message]"`

## End Change Validation Rules
When you call `dazbuild_end_change`, the following checks must pass:

1. **Pylint Score**: Must be 10/10 with no errors or warnings
2. **Unit Tests**: All tests must pass via `python -m unittest discover`
3. **Test Coverage**: Every .py file must contain at least one unittest.TestCase test
4. **No unittest.main()**: Files cannot invoke unittest.main() directly
5. **File Size Limit**: All code files must be smaller than 8192 bytes

## Code Quality Philosophy

### NEVER Optimize by Trimming Code
- **CRITICAL**: Never reduce file size by removing comments, shortening variable names, compacting formatting, or removing functionality
- **CRITICAL**: Never trim verbose code examples or documentation to meet size limits
- **CRITICAL**: Clean, verbose, readable code is THE TOP PRIORITY - never compromise this

### File Size Management - The RIGHT Way
- **When files exceed 8192 bytes**: ALWAYS refactor into multiple logical smaller files
- **Split by logical boundaries**: Create separate files for related functionality
- **Common refactoring patterns**:
  - Extract utility functions into `*_utils.py`
  - Split large classes into focused smaller classes
  - Create separate modules for different concerns (e.g., `*_processor.py`, `*_chat.py`, `*_viewer.js`)
  - Move test classes to separate test files if needed
- **Example**: If `script.js` is too large, split into `viewer.js`, `editor.js`, `ui.js`, etc.

## Best Practices for Using Dazbuild

### Work with Small References
- Always edit at the **smallest hierarchy node** possible
- Instead of rewriting entire files, target specific functions, methods, or classes
- Use `dazbuild_outline` to see the structure and find the right reference
- Example: Edit `myfile.py::MyClass::my_method` instead of `myfile.py`

### Workflow Pattern
1. `dazbuild_start_change` - Begin your change session
2. Use `dazbuild_get` to examine current code
3. Use `dazbuild_write` or `dazbuild_add` for targeted changes
4. `dazbuild_end_change` - Validate and commit

### Refactoring for Size Limits
- **Step 1**: Identify logical boundaries in the oversized file
- **Step 2**: Create new focused files for each logical group
- **Step 3**: Move code maintaining all functionality and verbose style
- **Step 4**: Update imports appropriately
- **Step 5**: Ensure all tests still pass

### Import Handling
- **Direct Execution vs Module Imports**: When files need to run both as scripts and as modules, use this pattern:
  ```python
  try:
      from .module_name import function_name
  except ImportError:
      # Fallback for direct execution
      from module_name import function_name
  ```
- **Optional Dependencies**: Handle external libraries gracefully:
  ```python
  try:
      import optional_library
      LIBRARY_AVAILABLE = True
  except ImportError:
      LIBRARY_AVAILABLE = False
  ```

### Testing Strategy
- Add real unit tests to every Python file (no mocks unless necessary)
- Test both happy path and edge cases
- Keep test methods focused and well-named
- **When Refactoring**: Update test imports when moving functions between modules
- **Pattern**: Test moved functions through their new module: `new_module.function_name()`

### Code Quality Standards
- Write clean, verbose, readable code that passes pylint
- Use meaningful, descriptive variable and function names
- Add comprehensive docstrings for public methods and classes
- Keep functions focused on a single responsibility
- **Preserve Comments**: Keep all explanatory comments and documentation
- **Verbose Examples**: Maintain clear, well-commented example code
- **Remove Unused Imports**: Pylint will catch these - clean them up promptly

### Framework Preservation
- **Respect Existing Architecture**: Don't change async frameworks (Sanic) to sync frameworks (Flask) without explicit permission
- **Maintain Async Patterns**: Keep `async def` functions and `await` calls when working with async frameworks
- **Add Routes Correctly**: For Sanic, use `@app.route()` decorators properly

## Architectural Principles

### Backend Purity Rule - CRITICAL
- **NEVER modify backend code to fix frontend display issues**
- **Backend Role**: Output data in the native format of the source framework (CadQuery, OpenCascade, etc.)
- **Frontend Role**: Adapt backend data to whatever rendering library is being used
- **Reason**: Maintains flexibility for future frontend changes and proper separation of concerns

### Frontend Display Issues - Always Fix on Frontend
- **Matrix format conversions**: Backend sends OpenCascade row-major, frontend converts to Three.js column-major
- **Coordinate system differences**: Backend uses CadQuery coordinates, frontend adapts to WebGL/Three.js
- **Rendering-specific transformations**: Color formats, geometry centering, camera positioning - all frontend
- **Display scaling, units, visual effects**: Always handled in frontend rendering code
- **Example**: CadQuery transformation matrices stay in OpenCascade format; Three.js frontend transposes them

### Data Flow Architecture
```
Backend (Pure) → Raw Data → Frontend (Adapts) → Display
CadQuery/OCC  →  Matrices  →  Three.js     →  WebGL
     |              |            |            |
   Native       Standard      Adapted     Rendered
  Format        Format       Format       Output
```

### Progressive Error Resolution
When `dazbuild_end_change` fails, fix issues in this order:
1. **File Size**: Extract large files into focused modules first (NEVER trim code)
2. **Pylint Issues**: Fix trailing whitespace, unused imports, line length
3. **Import Errors**: Add fallback imports for direct execution
4. **Test Failures**: Update test imports after refactoring
5. **Missing Functions**: Ensure all referenced functions exist in correct modules

### External Integration Patterns
- **LLM Integration**: Use structured responses with Pydantic models
- **Iterative Processing**: Implement retry loops with error accumulation
- **Graceful Degradation**: Provide fallbacks when external services unavailable
- **Error Context**: Include previous errors in retry attempts for better results

## File Size Crisis Response Protocol
If a file exceeds the 8192 byte limit:

1. **STOP**: Do not trim, compact, or remove any code
2. **ANALYZE**: Identify logical boundaries in the file
3. **PLAN**: Design how to split into smaller, focused files
4. **REFACTOR**: Create new files and move code groups
5. **TEST**: Ensure all functionality remains intact
6. **MAINTAIN**: Keep all verbose code, comments, and examples

Remember: Readable, maintainable code is worth more than any size optimization.
