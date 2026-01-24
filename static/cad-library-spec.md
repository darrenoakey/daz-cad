# CAD.js Library Specification

A CadQuery-like JavaScript library for creating 3D CAD models. All dimensions are in millimeters.

## Basic Pattern

Every CAD script must define a `result` variable that contains either a `Workplane` or an `Assembly`:

```javascript
const result = new Workplane("XY").box(20, 20, 20);
result;
```

## Workplane Class

### Constructor
```javascript
new Workplane(plane)
```
- `plane`: "XY", "XZ", or "YZ" - the initial work plane

### Primitives

**box(length, width, height, centered = true)**
- Creates a rectangular box
- If centered=true: centered on XY, bottom at Z=0 (default, good for 3D printing)
- If centered=false: corner at origin

**cylinder(radius, height, centered = true)**
- Creates a cylinder along Z axis
- Centered on XY, bottom at Z=0

**sphere(radius)**
- Creates a sphere centered at origin

**polygonPrism(sides, flatToFlat, height)**
- Creates a regular polygon extruded to a prism
- `sides`: Number of sides (3=triangle, 4=square, 6=hexagon, etc.)
- `flatToFlat`: Flat-to-flat distance (diameter of inscribed circle)
- `height`: Height of the prism
- Oriented with a flat edge at the top

### Operations

**hole(diameter, depth = null)**
- Creates a through-hole at the center of the shape along Z axis
- If depth is null, hole goes through entire shape

**chamfer(distance)**
- Applies chamfer to all edges (or selected edges)

**fillet(radius)**
- Applies fillet (rounded edge) to all edges (or selected edges)

**cutPattern(options)**
- Unified pattern cutting API - cuts lines, shapes, or grids into a face
- Use `.faces(">Z")` to select a face first, or it defaults to top face
- Options object:

  **Shape options:**
  - `shape`: Shape type or number of polygon sides. String values:
    - `'line'` - Rectangular groove (default)
    - `'rect'` or `'rectangle'` - Rectangle
    - `'square'` - Square
    - `'circle'` - Circle
    - `'hexagon'` or `'hex'` - Hexagon
    - `'octagon'` or `'oct'` - Octagon
    - `'triangle'` - Triangle
    - Or a number (3, 4, 5, 6, etc.) for any n-sided polygon
  - `width`: Primary dimension in mm - line width, rect width, circle diameter, polygon flat-to-flat (default 1.0)
  - `height`: Secondary dimension for rectangles, defaults to width
  - `length`: For lines only - line length, null = auto-fill face (default null)
  - `fillet`: Corner radius for rectangles/squares (default 0)
  - `roundEnds`: For lines - create stadium/pill shape with rounded ends (default false)
  - `shear`: Shear angle in degrees for parallelograms (default 0)
  - `rotation`: Rotate each individual shape by this angle in degrees (default 0)

  **Depth options:**
  - `depth`: Cut depth in mm, null = through-cut (default null)

  **Spacing options:**
  - `spacing`: Gap between shapes in mm (defaults to width, giving 50% solid / 50% cut)
  - `spacingX`: Override X gap
  - `spacingY`: Override Y gap
  - `wallThickness`: Alternative name for spacing - specify wall thickness between shapes

  **Border options:**
  - `border`: Margin from face edges in mm (default 2.0)
  - `borderX`: Override X border
  - `borderY`: Override Y border

  **Layout options:**
  - `columns`: Split pattern into N column groups (default 1)
  - `columnGap`: Gap between column groups in mm (default 5.0)
  - `rows`: Split pattern into N row groups (default null = 1)
  - `rowGap`: Gap between row groups in mm
  - `stagger`: Offset alternate rows for brick/honeycomb layout (default false)
  - `staggerAmount`: Fraction of spacingX to offset (default 0.5)
  - `angle`: For lines - rotation angle in degrees (default 0). 0=horizontal, 90=vertical, 45=diagonal

  **Backward compatibility:** `sides`, `type`, `size`, and `direction` still work

- Examples:
  ```javascript
  // Horizontal grip lines
  box.faces(">Z").cutPattern({
      shape: 'line',
      width: 1.0,
      spacing: 2.5,
      depth: 0.4,
      border: 3
  });

  // Honeycomb pattern (through-cut)
  box.faces(">Z").cutPattern({
      shape: 'hexagon',
      width: 8,
      wallThickness: 0.8,
      stagger: true
  });

  // Rounded rectangle grid
  box.faces(">Z").cutPattern({
      shape: 'rect',
      width: 10,
      height: 6,
      fillet: 2,
      spacing: 12
  });

  // Circle pattern
  box.faces(">Z").cutPattern({
      shape: 'circle',
      width: 5,  // diameter
      spacing: 8,
      depth: 2
  });
  ```

### Boolean Operations

**union(other)**
- Combines this shape with another (adds material)

**cut(other)**
- Subtracts another shape from this one (removes material)

**intersect(other)**
- Keeps only the overlapping region of two shapes

### Transformations

**translate(x, y, z)**
- Moves the shape by the specified amounts

**rotate(axisX, axisY, axisZ, angleDegrees)**
- Rotates around an axis through the origin
- Examples:
  - `rotate(0, 0, 1, 45)` - rotate 45 degrees around Z axis
  - `rotate(1, 0, 0, 90)` - rotate 90 degrees around X axis

### Selection (for targeted operations)

**faces(selector)**
- Selects faces for subsequent operations
- Selectors:
  - `">Z"` - top face (maximum Z)
  - `"<Z"` - bottom face (minimum Z)
  - `">X"`, `"<X"`, `">Y"`, `"<Y"` - similar for other axes

**edges(selector = null)**
- Selects edges of currently selected faces
- If no faces selected, selects all edges

### Appearance

**color(hexColor)**
- Sets the color of the shape
- Use CSS hex colors: `"#ff0000"` (red), `"#00ff00"` (green), `"#0000ff"` (blue)
- Common colors: `"#e74c3c"` (red), `"#2ecc71"` (green), `"#3498db"` (blue), `"#f39c12"` (orange), `"#9b59b6"` (purple)

## Assembly Class

For multi-part models with different colors (useful for multi-material 3D printing).

### Constructor
```javascript
new Assembly()
```

### Methods

**add(workplane)**
- Adds a Workplane part to the assembly
- Each part can have its own color

## Examples

### Simple Box
```javascript
const result = new Workplane("XY")
    .box(30, 20, 10);
result;
```

### Box with Hole
```javascript
const result = new Workplane("XY")
    .box(30, 30, 15)
    .hole(10)
    .chamfer(2);
result;
```

### Boolean Subtraction
```javascript
const box = new Workplane("XY").box(20, 20, 20);
const cyl = new Workplane("XY").cylinder(5, 25);
const result = box.cut(cyl);
result;
```

### Multi-Part Assembly
```javascript
// Red cube
const cube = new Workplane("XY")
    .box(20, 20, 20)
    .color("#e74c3c");

// Green cylinder offset to the right
const cylinder = new Workplane("XY")
    .cylinder(8, 25)
    .translate(30, 0, 0)
    .color("#2ecc71");

// Blue smaller cube offset to the left
const smallCube = new Workplane("XY")
    .box(12, 12, 15)
    .translate(-25, 0, 0)
    .color("#3498db");

const result = new Assembly()
    .add(cube)
    .add(cylinder)
    .add(smallCube);
result;
```

### Bracket Shape
```javascript
const base = new Workplane("XY").box(50, 30, 5);
const upright = new Workplane("XY")
    .box(5, 30, 40)
    .translate(-22.5, 0, 20);
const result = base.union(upright).fillet(2);
result;
```

### Hexagonal Prism
```javascript
const result = new Workplane("XY")
    .polygonPrism(6, 20, 15)
    .color("#9b59b6");
result;
```

### Honeycomb Panel
```javascript
const result = new Workplane("XY")
    .box(60, 40, 4)
    .faces(">Z").cutPattern({
        shape: 'hexagon',
        width: 8,
        wallThickness: 0.8,
        border: 3,
        stagger: true
    })
    .color("#f39c12");
result;
```

### Grip Lines on Surface
```javascript
const result = new Workplane("XY")
    .box(80, 40, 5)
    .faces(">Z").cutPattern({
        shape: 'line',
        width: 1.2,
        spacing: 3,
        depth: 0.5,
        border: 5,
        angle: 0  // horizontal lines (90 for vertical, 45 for diagonal)
    })
    .color("#3498db");
result;
```

### Open Tray with Chamfered Base
```javascript
// Create shell by boolean subtraction
const outer = new Workplane("XY").box(80, 40, 42);
const inner = new Workplane("XY")
    .box(76, 38, 40)
    .translate(0, 1, 2);  // offset to leave walls
const shell = outer.cut(inner);

// Chamfer bottom edges, fillet the rest
const result = shell
    .faces("<Z").edges().chamfer(1)
    .fillet(0.4)
    .color("#3498db");
result;
```

## Tips

1. Always end with `result;` to return the final shape
2. Chain operations fluently: `.box().hole().chamfer()`
3. Use Assembly for multi-color prints
4. Shapes are positioned for 3D printing by default (bottom at Z=0)
5. Boolean operations create new shapes - assign to variables
