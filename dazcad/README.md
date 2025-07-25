# DazCAD - Simple CadQuery Runner

A minimal web-based CadQuery development environment with 3D visualization.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. Run the server:
   ```bash
   python server.py
   ```

2. Open http://localhost:8000 in your browser

3. Write CadQuery code in the left editor panel

4. Click "Run" or press Ctrl+Enter to execute

5. View the 3D result on the right (use mouse to rotate/zoom)

## Example Code

```python
import cadquery as cq

# Create a simple box
box = cq.Workplane("XY").box(10, 10, 10)

# Show the result
show_object(box, "MyBox", "#FF0000")
```

## Features

- Live CadQuery code execution
- 3D visualization with Three.js
- Mouse-controlled camera (rotate/zoom/pan)
- Colored object support
- Error handling and output display