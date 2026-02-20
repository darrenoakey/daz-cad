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

**ellipsoid(rx, ry, rz)**
- Creates an ellipsoid centered at origin (non-uniformly scaled sphere)
- `rx`: Semi-axis length in X (total X diameter = 2*rx)
- `ry`: Semi-axis length in Y (total Y diameter = 2*ry)
- `rz`: Semi-axis length in Z (total Z diameter = 2*rz)
- Use as a cutter with `.cut()` to carve elliptical bowls, indentations, etc.

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

**clean(options?)**
- Optimizes geometry after boolean operations
- Merges coplanar faces and collinear edges
- Fixes geometry issues
- Options: `{ unifyFaces: true, unifyEdges: true, fix: true, rebuildSolid: false }`
- Use after pattern cuts if geometry appears messy

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

  **Clipping options (for non-rectangular faces):**
  - `clip`: How to handle shapes at face boundaries. Values:
    - `'none'` - No clipping (default, backward compatible)
    - `'partial'` - Clip shapes at face boundary, creating partial shapes at edges
    - `'whole'` - Only keep shapes fully inside boundary, no partial shapes

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

  // Hex pattern on circular face with partial clipping
  cylinder.faces(">Z").cutPattern({
      shape: 'hexagon',
      width: 6,
      wallThickness: 1,
      stagger: true,
      clip: 'partial',  // Clips hexagons at circular boundary
      border: 2
  });

  // Hex pattern on circular face - whole shapes only
  cylinder.faces(">Z").cutPattern({
      shape: 'hexagon',
      width: 6,
      wallThickness: 1,
      stagger: true,
      clip: 'whole',  // Only complete hexagons, no partial shapes
      border: 2
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
- Selectors:
  - `"|Z"` - edges parallel to Z axis (vertical)
  - `"|X"`, `"|Y"` - edges parallel to X/Y axis
  - `">Z"` - edges at maximum Z position (top)
  - `"<Z"` - edges at minimum Z position (bottom)
  - `">X"`, `"<X"`, `">Y"`, `"<Y"` - edges at max/min on X/Y axis
- Compound selectors:
  - `"<X and <Y"` - edges matching BOTH conditions (intersection)
  - `"<X or |Z"` - edges matching EITHER condition (union)
  - Example: `edges("<X and <Y")` selects the single corner edge at min X and min Y

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

### Elliptical Bowl
```javascript
// Carve an elliptical bowl into a block
const block = new Workplane("XY").box(70, 45, 15);
const cutter = new Workplane("XY")
    .ellipsoid(32, 18.5, 10)   // 64mm x 37mm x 20mm
    .translate(0, 0, 15);       // position at top of block
const result = block.cut(cutter)
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

## Gridfinity Module

The Gridfinity module provides standardized gridfinity-compatible bins, plugs, baseplates, and optimized cutout grids. **Always use these when the user asks for gridfinity anything** — do not manually create gridfinity shapes with box/translate.

The module is automatically available (imported by the worker). Use `Gridfinity.bin()`, `Gridfinity.plug()`, etc. directly.

### Gridfinity.bin(options)

Creates a solid gridfinity bin with standardized stepped base profile (compatible with gridfinity baseplates).

- `x`: X dimension in grid units (1 unit = 42mm)
- `y`: Y dimension in grid units
- `z`: Z dimension in height units (1 unit = 7mm)
- `stackable` (optional, default false): Include stacking lip at top
- `solid` (optional, default true): If false, creates hollow shell with 1.2mm walls

Returns a Workplane with gridfinity metadata (infill settings, minCutZ for automatic cut depth).

```javascript
// Basic 2x1 bin, 5 units high
const result = Gridfinity.bin({ x: 2, y: 1, z: 5 })
    .color("#3498db");
result;
```

### Gridfinity.plug(options)

Creates a solid insert plug that fits inside a gridfinity bin (with proper clearances).

- `x`: X dimension in grid units
- `y`: Y dimension in grid units
- `z`: Z dimension in height units
- `tolerance` (optional, default 0.30): Wall clearance in mm
- `stackable` (optional, default true): Account for stacking lip gap

```javascript
// Insert plug for a 2x3 bin
const result = Gridfinity.plug({ x: 2, y: 3, z: 3 })
    .cutCircleGrid({ diameter: 20, count: 4 })
    .color("#2ecc71");
result;
```

### Gridfinity.baseplate(options)

Creates a minimal gridfinity baseplate (open grid frame, no solid floor).

- `x`: X dimension in grid units
- `y`: Y dimension in grid units
- `fillet` (optional, default true): Round outer corners
- `chamfer` (optional, default true): Chamfer bottom edge for bed adhesion

```javascript
const result = Gridfinity.baseplate({ x: 3, y: 2 })
    .color("#95a5a6");
result;
```

### Gridfinity.fitBin(options)

Creates a bin with multiple custom-sized cutouts, automatically finding the smallest bin that fits all cuts. Uses shelf-packing with centering.

- `cuts`: Array of `[width, height]` or `{width, height, fillet?}` objects
- `z`: Height in gridfinity height units
- `spacing` (optional, default 1.5): Minimum spacing between cuts in mm
- `fillet` (optional, default 3): Default corner fillet radius in mm

```javascript
// Three different compartments, auto-sized bin
const result = Gridfinity.fitBin({
    cuts: [[80, 40], [30, 20], [35, 20]],
    z: 3
}).color("#e67e22");
result;

// With custom fillets per cut
const result = Gridfinity.fitBin({
    cuts: [
        { width: 80, height: 40, fillet: 5 },
        { width: 30, height: 20 },
        { width: 35, height: 20, fillet: 0 }
    ],
    z: 4,
    spacing: 2
}).color("#3498db");
result;
```

### .cutRectGrid(options)

Workplane method. Cuts an optimized grid of rectangular pockets into a shape. Automatically calculates optimal layout and spacing. Respects gridfinity `minCutZ` metadata (won't cut into the base).

- `width`: Pocket width in mm
- `height`: Pocket height in mm
- `count` (optional, default null): Target count (null = maximize)
- `fillet` (optional, default 0): Corner fillet radius in mm
- `depth` (optional, default null): Cut depth (null = auto from shape height or minCutZ)
- `minBorder` (optional, default 2.0): Minimum shell thickness in mm
- `minSpacing` (optional, default 0.6): Minimum spacing between cutouts in mm

```javascript
const result = Gridfinity.bin({ x: 3, y: 2, z: 5 })
    .cutRectGrid({ width: 30, height: 40, count: 2, fillet: 3 })
    .color("#3498db");
result;
```

### .cutCircleGrid(options)

Workplane method. Cuts an optimized grid of circular pockets. Same auto-layout behavior as cutRectGrid.

- `radius`: Circle radius in mm (or use `diameter`)
- `diameter`: Circle diameter in mm (alternative to radius)
- `count` (optional, default null): Target count (null = maximize)
- `depth` (optional, default null): Cut depth (null = auto)
- `minBorder` (optional, default 2.0): Minimum shell thickness in mm
- `minSpacing` (optional, default 2.0): Minimum spacing between circles in mm

```javascript
const result = Gridfinity.bin({ x: 2, y: 2, z: 4 })
    .cutCircleGrid({ diameter: 25 })
    .color("#9b59b6");
result;
```

### .addBaseplate(options)

Workplane method. Adds a gridfinity baseplate onto a selected face (or top face). Auto-calculates how many grid cells fit.

- `fillet` (optional, default true): Round outer corners

```javascript
// Box with baseplate on top
const result = new Workplane("XY")
    .box(150, 100, 10)
    .faces(">Z")
    .addBaseplate()
    .color("#3498db");
result;
```

### Gridfinity Examples

```javascript
// Pen holder: 2x1 bin with circle grid
const result = Gridfinity.bin({ x: 2, y: 1, z: 5 })
    .cutCircleGrid({ diameter: 14 })
    .color("#2ecc71");
result;
```

```javascript
// Tool organizer with custom compartments
const result = Gridfinity.fitBin({
    cuts: [[60, 35], [25, 25], [25, 25], [40, 35]],
    z: 4
}).color("#e74c3c");
result;
```

```javascript
// Bin with ellipsoid scoop cutout
const bin = Gridfinity.bin({ x: 2, y: 1, z: 5 });
const cutter = new Workplane("XY")
    .ellipsoid(34, 19, 30)
    .translate(0, 0, 49);  // position at top
const result = bin.cut(cutter).color("#3498db");
result;
```

## Named References

Shapes get automatic semantic face names that survive transforms and boolean operations. Convention: Front=+Y, Back=-Y, Right=+X, Left=-X, Top=+Z, Bottom=-Z.

### Auto-Named Faces

**box()** automatically names all 6 faces: `front`, `back`, `right`, `left`, `top`, `bottom`

**cylinder()** automatically names: `top`, `bottom`, `side`

### Face/Edge Selection by Name
```javascript
shape.faces("front")       // select front face (same as faces(">Y") on unrotated box)
shape.edges("front-top")   // select edge between front and top faces
shape.face("front")        // get FaceRef { normal, centroid, area } for inspection
```

After transforms, names follow the geometry:
```javascript
const box = new Workplane("XY").box(10, 10, 10);
const rotated = box.rotate(0, 0, 1, 90);
rotated.faces("front")  // selects the face now at -X (was +Y before rotation)
```

### Custom Naming
```javascript
shape.name("bracket")           // name the whole shape for sub-part access
shape.nameFace(">Z", "lid")     // add custom name for a face
shape.nameEdge(">Z and >Y", "rim")  // add custom name for edge(s)
```

### Relative Operations

**extrudeOn(faceName, width, height, depth)** — extrude box outward from named face, auto-union
```javascript
const result = new Workplane("XY").box(20, 20, 20)
    .extrudeOn("front", 5, 5, 3);  // 3mm protrusion from front face
```

**extrudeOn(faceName, otherShape)** — position other shape on face, auto-union

**cutInto(faceName, width, height, depth)** — cut pocket inward from named face
```javascript
const result = new Workplane("XY").box(20, 20, 20)
    .cutInto("top", 8, 8, 3);  // 3mm pocket from top
```

**cutInto(faceName, otherShape)** — position other shape against face, cut

**centerOn(other, faceName)** — center this shape on other's named face
```javascript
const knob = new Workplane("XY").cylinder(3, 5);
const positioned = knob.centerOn(base, "top");
```

**alignTo(other, faceName)** — align this shape against other's named face

**attachTo(other, faceName)** — place on face and union (= centerOn + union)
```javascript
const result = knob.attachTo(base, "top");  // center on top + union
```

### Sub-Part Access After Boolean
```javascript
const base = new Workplane("XY").box(20, 20, 10).name("base");
const tab = new Workplane("XY").box(5, 5, 5).translate(0, 0, 10).name("tab");
const merged = base.union(tab);

merged.faces("base.front")  // dotted sub-part access
merged.faces("front")       // also works (top-level lookup)
```

## Tips

1. Always end with `result;` to return the final shape
2. Chain operations fluently: `.box().hole().chamfer()`
3. Use Assembly for multi-color prints
4. Shapes are positioned for 3D printing by default (bottom at Z=0)
5. Boolean operations create new shapes - assign to variables
6. **For gridfinity items, always use the Gridfinity module** — never manually build gridfinity geometry with boxes
7. Use named references (`"front"`, `"top"`) instead of axis selectors for clearer, rotation-safe code
