# DazCAD - Simple CadQuery Runner

A minimal web-based CadQuery development environment with 3D visualization.

## Installation

```bash
pip install -r requirements.txt
```

Note: CadQuery requires Python 3.8+ and may have additional system dependencies. See the [CadQuery installation guide](https://cadquery.readthedocs.io/en/latest/installation.html) for details.

## Usage

1. Run the server:
   ```bash
   python server.py
   ```

2. Open http://localhost:8000 in your browser

3. Write CadQuery code in the left editor panel

4. Click "Run" or press Ctrl+Enter to execute

5. View the 3D result on the right (use mouse to rotate/zoom)

The server runs in debug mode with auto-reload enabled, so any changes to the server files will automatically restart the server.

## Example Code

The default example shows how to create an assembly with multiple colored parts:

```python
import cadquery as cq
from cadquery import Color

# Create an assembly with two colored boxes
assembly = cq.Assembly()

# Create first box (red)
box1 = cq.Workplane("XY").box(10, 10, 10)
assembly.add(box1, name="RedBox", color=Color("red"))

# Create second box (blue) positioned to the right
box2 = cq.Workplane("XY").box(10, 10, 10)
assembly.add(box2, name="BlueBox", loc=cq.Location((15, 0, 0)), color=Color("blue"))

# Show the assembly - it contains both colored parts
show_object(assembly, "ColoredAssembly")
```

## Features

- Live CadQuery code execution
- 3D visualization with Three.js
- Mouse-controlled camera (rotate/zoom/pan)
- Support for CadQuery Assemblies with multiple colored parts
- Error handling and output display
- Auto-reload on file changes (debug mode)

## Troubleshooting

If you encounter import errors with OCP or CadQuery:
- Make sure you have Python 3.8 or later
- Consider using a conda environment: `conda install -c conda-forge cadquery`
- Check the CadQuery documentation for platform-specific installation instructions