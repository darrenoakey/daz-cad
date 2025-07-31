# DazCAD - Simple CadQuery Runner

A minimal web-based CadQuery development environment with 3D visualization, optimized for 3D printing workflows.

## Installation

```bash
pip install -r requirements.txt
```

Note: CadQuery requires Python 3.8+ and may have additional system dependencies. See the [CadQuery installation guide](https://cadquery.readthedocs.io/en/latest/installation.html) for details.

## Usage

1. Run the server:
   ```bash
   python dazcad/server.py
   ```

2. Open http://localhost:8000 in your browser

3. Write CadQuery code in the left editor panel

4. Click "Run" or press Ctrl+Enter to execute

5. View the 3D result on the right (use mouse to rotate/zoom)

The server runs in debug mode with auto-reload enabled, so any changes to the server files will automatically restart the server.

## Example Code

The default example shows how to create an assembly with multiple colored parts positioned for 3D printing:

```python
import cadquery as cq
from cadquery import Color

# Create an assembly with two colored boxes positioned for 3D printing
assembly = cq.Assembly()

# Create first box (red) - positioned to sit on build plate (z=0)
box1 = cq.Workplane("XY").workplane(offset=5).box(10, 10, 10)
assembly.add(box1, name="RedBox", color=Color("red"))

# Create second box (blue) positioned to the right - also on build plate
box2 = cq.Workplane("XY").workplane(offset=5).box(10, 10, 10)
assembly.add(box2, name="BlueBox", loc=cq.Location((15, 0, 0)), color=Color("blue"))

# Show the assembly - it contains both colored parts sitting on z=0
show_object(assembly, "ColoredAssembly")
```

## 3D Printing Ready

All examples and templates in DazCAD are designed for 3D printing:
- Models are positioned to sit flat on the build plate (z=0 plane)
- No parts extend below z=0 
- Proper support for STL, STEP, and 3MF export formats
- Built-in library of 3D printable examples

## Features

- Live CadQuery code execution
- 3D visualization with Three.js
- Mouse-controlled camera (rotate/zoom/pan)
- Support for CadQuery Assemblies with multiple colored parts
- Full error handling with stack traces and line numbers
- Auto-run when loading library examples
- Export to STL, STEP, and 3MF formats
- Auto-reload on file changes (debug mode)

## Troubleshooting

If you encounter import errors with OCP or CadQuery:
- Make sure you have Python 3.8 or later
- Consider using a conda environment: `conda install -c conda-forge cadquery`
- Check the CadQuery documentation for platform-specific installation instructions