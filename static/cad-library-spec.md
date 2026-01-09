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

### Operations

**hole(diameter, depth = null)**
- Creates a through-hole at the center of the shape along Z axis
- If depth is null, hole goes through entire shape

**chamfer(distance)**
- Applies chamfer to all edges (or selected edges)

**fillet(radius)**
- Applies fillet (rounded edge) to all edges (or selected edges)

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

## Tips

1. Always end with `result;` to return the final shape
2. Chain operations fluently: `.box().hole().chamfer()`
3. Use Assembly for multi-color prints
4. Shapes are positioned for 3D printing by default (bottom at Z=0)
5. Boolean operations create new shapes - assign to variables
