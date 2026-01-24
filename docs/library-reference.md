# DAZ-CAD-2 Library Reference

Complete API documentation for the CAD library.

## Table of Contents

- [Workplane Class](#workplane-class)
  - [Primitives](#primitives)
  - [Boolean Operations](#boolean-operations)
  - [Transformations](#transformations)
  - [Edge and Face Selection](#edge-and-face-selection)
  - [Edge Treatments](#edge-treatments)
  - [Patterns](#patterns)
  - [Metadata](#metadata)
  - [Colors and Modifiers](#colors-and-modifiers)
- [Gridfinity Module](#gridfinity-module)
  - [Creating Bins, Plugs, and Baseplates](#creating-bins-plugs-and-baseplates)
  - [Cutout Grids](#cutout-grids)
  - [Auto-Fit Packing](#auto-fit-packing)
- [Assembly Class](#assembly-class)
- [Utility Classes](#utility-classes)

---

## Workplane Class

The main class for creating and manipulating 3D geometry.

### Constructor

```javascript
new Workplane(plane = "XY")
```

Creates a new workplane on the specified plane.

**Parameters:**
- `plane` - One of `"XY"`, `"XZ"`, or `"YZ"`

**Example:**
```javascript
const wp = new Workplane("XY");
```

---

## Primitives

### box(length, width, height, centered = true)

Creates a rectangular box.

**Parameters:**
- `length` - X dimension in mm
- `width` - Y dimension in mm
- `height` - Z dimension in mm
- `centered` - If true, centers on XY with bottom at Z=0

**Example:**
```javascript
const box = new Workplane("XY").box(50, 30, 20);
```

---

### cylinder(radius, height) | cylinder({ height, diameter })

Creates a cylinder along the Z axis.

**Parameters (signature 1):**
- `radius` - Cylinder radius in mm
- `height` - Cylinder height in mm

**Parameters (signature 2):**
- `height` - Cylinder height in mm
- `diameter` - Cylinder diameter in mm (alternative to radius)

**Examples:**
```javascript
const cyl1 = new Workplane("XY").cylinder(10, 30);
const cyl2 = new Workplane("XY").cylinder({ diameter: 20, height: 30 });
```

---

### sphere(radius)

Creates a sphere centered at the origin.

**Parameters:**
- `radius` - Sphere radius in mm

**Example:**
```javascript
const ball = new Workplane("XY").sphere(15);
```

---

### polygonPrism(sides, flatToFlat, height)

Creates a regular polygon prism (extruded polygon).

**Parameters:**
- `sides` - Number of sides (3, 4, 5, 6, etc.)
- `flatToFlat` - Distance between parallel flats in mm
- `height` - Height of the prism in mm

**Example:**
```javascript
// Create a hexagonal prism
const hex = new Workplane("XY").polygonPrism(6, 20, 10);
```

---

### text(textString, fontSize, depth = null, fontName = null)

Creates 3D extruded text.

**Parameters:**
- `textString` - The text to render
- `fontSize` - Height of the text in mm
- `depth` - Extrusion depth (defaults to fontSize/5)
- `fontName` - Font name (uses Overpass Bold if null)

**Prerequisites:**
Call `await loadFont(url)` before using text.

**Example:**
```javascript
await loadFont('/static/fonts/Overpass-Bold.ttf');
const label = new Workplane("XY").text("HELLO", 10, 2);
```

---

## Boolean Operations

### union(other)

Combines two shapes into one.

**Parameters:**
- `other` - Another Workplane to combine with

**Example:**
```javascript
const combined = box.union(cylinder);
```

---

### cut(other)

Subtracts one shape from another.

**Parameters:**
- `other` - Shape to subtract

**Example:**
```javascript
const boxWithHole = box.cut(cylinder);
```

---

### intersect(other)

Creates the intersection of two shapes.

**Parameters:**
- `other` - Shape to intersect with

**Example:**
```javascript
const common = box.intersect(sphere);
```

---

### hole(diameter, depth = null)

Creates a centered hole through the shape along the Z axis.

**Parameters:**
- `diameter` - Hole diameter in mm
- `depth` - Hole depth (null = through-hole)

**Example:**
```javascript
const boxWithHole = new Workplane("XY")
    .box(50, 50, 20)
    .hole(10);
```

---

## Transformations

### translate(x, y, z)

Moves the shape.

**Parameters:**
- `x`, `y`, `z` - Translation distances in mm

**Example:**
```javascript
const moved = box.translate(10, 0, 5);
```

---

### rotate(axisX, axisY, axisZ, angleDegrees)

Rotates the shape around an axis through the origin.

**Parameters:**
- `axisX`, `axisY`, `axisZ` - Rotation axis vector
- `angleDegrees` - Rotation angle in degrees

**Examples:**
```javascript
// Rotate 45 degrees around Z axis
const rotated = box.rotate(0, 0, 1, 45);

// Rotate 90 degrees around X axis
const flipped = box.rotate(1, 0, 0, 90);
```

---

## Edge and Face Selection

### faces(selector = null)

Selects faces matching a selector.

**Selectors:**
- `">Z"` - Face(s) with maximum Z (top)
- `"<Z"` - Face(s) with minimum Z (bottom)
- `">X"`, `"<X"`, `">Y"`, `"<Y"` - Similar for other axes
- `"|Z"` - Faces parallel to Z axis

**Example:**
```javascript
const topFace = box.faces(">Z");
```

---

### facesNot(selector)

Selects all faces except those matching the selector.

**Example:**
```javascript
// All faces except the bottom
const notBottom = box.facesNot("<Z");
```

---

### edges(selector = null)

Selects edges. If faces are selected, selects edges of those faces.

**Selectors:**
- `"|Z"` - Edges parallel to Z axis (vertical edges)
- `"|X"`, `"|Y"` - Edges parallel to X/Y axis
- `">Z"`, `"<Z"` - Edges with max/min Z position

**Example:**
```javascript
// Fillet only vertical edges
const filleted = box.edges("|Z").fillet(2);
```

---

### edgesNot(selector)

Selects all edges except those matching the selector.

**Example:**
```javascript
// All edges except vertical ones
const horizontalEdges = box.edgesNot("|Z");
```

---

### filterEdges(predicate)

Filters edges using a custom function.

**Parameters:**
- `predicate` - Function receiving `{ zMin, zMax, edge }` and returning boolean

**Example:**
```javascript
// Only edges above Z=5
const highEdges = box.edges().filterEdges(e => e.zMin > 5);
```

---

### filterOutBottom()

Removes edges at the bottom of the shape from selection.

**Example:**
```javascript
const notBottomEdges = box.edges().filterOutBottom();
```

---

### filterOutTop()

Removes edges at the top of the shape from selection.

**Example:**
```javascript
const notTopEdges = box.edges().filterOutTop();
```

---

## Edge Treatments

### fillet(radius)

Applies rounded fillets to selected edges.

**Parameters:**
- `radius` - Fillet radius in mm

**Example:**
```javascript
// Fillet all edges
const rounded = box.fillet(2);

// Fillet only top edges
const roundedTop = box.faces(">Z").edges().fillet(2);
```

---

### chamfer(distance)

Applies 45-degree chamfers to selected edges.

**Parameters:**
- `distance` - Chamfer distance in mm

**Example:**
```javascript
// Chamfer bottom edges
const chamfered = box.faces("<Z").edges().chamfer(1);
```

---

## Patterns

### cutPattern(options)

Unified pattern cutting API. Cuts lines, shapes, or grids into a selected face.

**Usage:** Select a face first with `.faces()`, or it defaults to the top face.

**Shape Options:**
- `shape` - Shape type: `'line'`, `'rect'`, `'square'`, `'circle'`, `'hexagon'`, `'octagon'`, `'triangle'`, or a number for n-sided polygons (default `'line'`)
- `width` - Primary dimension: line width, rect width, circle diameter, polygon flat-to-flat (default 1.0)
- `height` - Secondary dimension for rectangles (defaults to width)
- `length` - For lines: line length, null = auto-fill (default null)
- `fillet` - Corner radius for rectangles/squares (default 0)
- `roundEnds` - For lines: create stadium/pill shape (default false)
- `shear` - Shear angle in degrees (default 0)
- `rotation` - Rotate each individual shape in degrees (default 0)

**Depth Options:**
- `depth` - Cut depth in mm, null = through-cut (default null)

**Spacing Options:**
- `spacing` - Gap between shapes in mm (defaults to width, giving 50% solid / 50% cut)
- `spacingX` / `spacingY` - Override per-axis gap
- `wallThickness` - Alternative name for spacing: wall thickness between shapes

**Border Options:**
- `border` - Margin from face edges (default 2.0)
- `borderX` / `borderY` - Override per-axis borders

**Layout Options:**
- `columns` - Split into N column groups (default 1)
- `columnGap` - Gap between column groups (default 5.0)
- `rows` / `rowGap` - Split into row groups
- `stagger` - Offset alternate rows for brick/honeycomb layout (default false)
- `staggerAmount` - Fraction of spacingX to offset (default 0.5)
- `angle` - For lines: rotation angle in degrees (default 0). 0=horizontal, 90=vertical, 45=diagonal

**Backward Compatibility:** `sides`, `type`, `size`, and `direction` parameters still work.

**Examples:**
```javascript
// Horizontal grip lines
const grooved = box.faces(">Z").cutPattern({
    shape: 'line',
    width: 1.0,
    spacing: 2.5,
    depth: 0.4,
    border: 3
});

// Honeycomb through-cut
const honeycomb = box.faces(">Z").cutPattern({
    shape: 'hexagon',
    width: 8,
    wallThickness: 0.8,
    stagger: true
});

// Rounded rectangle pattern
const rounded = box.faces(">Z").cutPattern({
    shape: 'rect',
    width: 10,
    height: 6,
    fillet: 2,
    spacing: 12,
    depth: 2
});
```

---

## Metadata

### meta(key, value?)

Gets or sets generic metadata.

**Parameters:**
- `key` - Metadata key string
- `value` - Value to set (omit to get current value)

**Returns:** New Workplane if setting, or current value if getting

**Example:**
```javascript
const part = box.meta('category', 'storage');
console.log(part.meta('category')); // 'storage'
```

---

### infillDensity(percent)

Sets infill density for 3MF export.

**Parameters:**
- `percent` - Infill percentage (e.g., 5, 15, 20)

**Example:**
```javascript
const lightPart = box.infillDensity(5);
```

---

### infillPattern(pattern)

Sets infill pattern for 3MF export.

**Parameters:**
- `pattern` - One of: `'grid'`, `'gyroid'`, `'honeycomb'`, `'triangles'`, `'cubic'`, `'line'`, `'concentric'`

**Example:**
```javascript
const gyroidFill = box.infillPattern('gyroid');
```

---

### partName(name)

Sets the part name for 3MF export.

**Parameters:**
- `name` - Part name string

**Example:**
```javascript
const namedPart = box.partName('Storage Bin');
```

---

## Colors and Modifiers

### color(hexColor)

Sets the color of the shape.

**Parameters:**
- `hexColor` - CSS hex color string (e.g., `"#ff0000"`, `"red"`)

**Example:**
```javascript
const redBox = box.color("#ff0000");
const blueBox = box.color("blue");
```

---

### asModifier()

Marks the shape as a modifier volume for multi-material 3MF export.

**Example:**
```javascript
const colorZone = cylinder.color("#00ff00").asModifier();
```

---

### withModifier(modifier)

Attaches a modifier volume to this part.

**Parameters:**
- `modifier` - A Workplane marked as modifier

**Example:**
```javascript
const part = box.withModifier(colorZone);
```

---

## Gridfinity Module

### Creating Bins, Plugs, and Baseplates

#### Gridfinity.bin(options)

Creates a Gridfinity-compatible bin with standardized base profile.

**Options:**
- `x` - X dimension in grid units (1 unit = 42mm)
- `y` - Y dimension in grid units
- `z` - Z dimension in height units (1 unit = 7mm)
- `stackable` - Include stacking lip (default false, not yet implemented)
- `solid` - Create solid or hollow shell (default true)

**Example:**
```javascript
const bin = Gridfinity.bin({ x: 2, y: 2, z: 3 });
```

---

#### Gridfinity.plug(options)

Creates a solid insert plug that fits inside a bin.

**Options:**
- `x`, `y`, `z` - Dimensions in grid/height units
- `tolerance` - Wall clearance in mm (default 0.30)
- `stackable` - Account for stacking lip (default true)

**Example:**
```javascript
const plug = Gridfinity.plug({ x: 2, y: 2, z: 3 });
```

---

#### Gridfinity.baseplate(options)

Creates a minimal Gridfinity baseplate (no magnets). This is the thinnest possible baseplate - an open grid structure with just the stepped rim profile that bins clip into (no solid floor).

**Options:**
- `x` - X dimension in grid units (1 unit = 42mm)
- `y` - Y dimension in grid units

**Example:**
```javascript
// Create a 3x2 baseplate (open grid)
const plate = Gridfinity.baseplate({ x: 3, y: 2 });
```

---

#### addBaseplate(options?)

Adds a gridfinity baseplate onto a selected face. Use `.faces()` to select a face first. Automatically calculates the largest baseplate that fits on that face.

**Options:**
- `fillet` - Round outer corners (default: true)

**Example:**
```javascript
// Add baseplate to the top face of a box
const boxWithPlate = new Workplane("XY")
    .box(150, 100, 10)
    .faces(">Z")
    .addBaseplate();

// Without rounded corners
const sharpPlate = myShape.faces(">Z").addBaseplate({ fillet: false });
```

---

### Cutout Grids

#### cutRectGrid(options)

Cuts a grid of rectangular pockets with automatic spacing optimization.

**Options:**
- `width` - Pocket width in mm
- `height` - Pocket height in mm
- `count` - Target count (null = maximize)
- `fillet` - Corner fillet radius (default 0)
- `depth` - Cut depth (null = auto-calculate)
- `minBorder` - Minimum shell thickness (default 2.0)
- `minSpacing` - Minimum spacing between cutouts (default 0.6)

**Example:**
```javascript
const bin = Gridfinity.bin({ x: 2, y: 2, z: 3 })
    .cutRectGrid({
        width: 30,
        height: 40,
        fillet: 3,
        minBorder: 2
    });
```

---

#### cutCircleGrid(options)

Cuts a grid of circular pockets with automatic spacing optimization.

**Options:**
- `radius` or `diameter` - Circle size in mm
- `count` - Target count (null = maximize)
- `depth` - Cut depth (null = auto-calculate)
- `minBorder` - Minimum shell thickness (default 2.0)
- `minSpacing` - Minimum spacing between circles (default 2.0)

**Example:**
```javascript
const bin = Gridfinity.bin({ x: 3, y: 2, z: 4 })
    .cutCircleGrid({
        diameter: 20,
        minSpacing: 3
    });
```

---

### Auto-Fit Packing

#### Gridfinity.fitBin(options)

Creates a bin with multiple custom-sized cutouts, automatically finding the smallest bin that fits.

**Options:**
- `cuts` - Array of cutouts. Each can be:
  - `[width, height]` - Simple array format
  - `{ width, height, fillet? }` - Object format with optional fillet
- `z` - Height in Gridfinity units
- `spacing` - Minimum spacing between cuts (default 1.5mm)
- `fillet` - Default corner fillet for all cuts (default 3mm)

**Example:**
```javascript
const bin = Gridfinity.fitBin({
    cuts: [
        [80, 40],                              // 80x40mm rectangle
        [30, 20],                              // 30x20mm rectangle
        { width: 35, height: 20, fillet: 5 }   // Custom fillet
    ],
    z: 3,
    spacing: 1.5
});
```

---

### Gridfinity Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `Gridfinity.UNIT_SIZE` | 42mm | Grid unit size |
| `Gridfinity.UNIT_HEIGHT` | 7mm | Height per z-unit |
| `Gridfinity.BIN_CLEARANCE` | 0.25mm | Clearance from bin exterior |
| `Gridfinity.OUTER_RADIUS` | 3.75mm | Corner radius of bin |
| `Gridfinity.WALL_THICKNESS` | 1.2mm | Shell thickness |
| `Gridfinity.BASE_HEIGHT` | 4.75mm | Total base height |
| `Gridfinity.TOLERANCE` | 0.30mm | Default plug tolerance |
| `Gridfinity.BP_HEIGHT` | 4.65mm | Baseplate rim height |
| `Gridfinity.BP_FLOOR` | 1.0mm | Default baseplate floor thickness |

---

## Assembly Class

The Assembly class combines multiple parts for export.

### Constructor

```javascript
new Assembly()
```

### add(workplane, name?)

Adds a part to the assembly.

**Parameters:**
- `workplane` - A Workplane with geometry
- `name` - Optional part name

**Example:**
```javascript
const assembly = new Assembly()
    .add(baseBox, "Base")
    .add(lid, "Lid")
    .add(handle, "Handle");
```

### getMeshes()

Returns array of mesh data for rendering/export.

---

## Utility Classes

### Profiler

Measures timing of CAD operations.

```javascript
const profile = new Profiler('Build Name');
// ... operations ...
profile.checkpoint('step 1');
// ... more operations ...
profile.checkpoint('step 2');
profile.finished();  // Logs timing table
```

### loadFont(url, fontName?)

Loads a font for text rendering.

```javascript
await loadFont('/static/fonts/Overpass-Bold.ttf');
```

---

## Complete Examples

### Storage Bin with Dividers

```javascript
// Create a 3x2 bin with two rectangular compartments
const bin = Gridfinity.bin({ x: 3, y: 2, z: 4 })
    .cutRectGrid({
        width: 40,
        height: 60,
        count: 2,
        fillet: 5,
        minBorder: 3
    })
    .color("#3498db");
```

### Multi-Color Part

```javascript
// Main box
const box = new Workplane("XY")
    .box(50, 50, 20)
    .color("#ffffff");

// Colored accent region
const accent = new Workplane("XY")
    .box(40, 40, 5)
    .translate(0, 0, 15)
    .color("#ff0000")
    .asModifier();

// Combine
const result = box.withModifier(accent);
```

### Open Box with Honeycomb Base

```javascript
const LENGTH = 80;
const WIDTH = 40;
const WALL_HEIGHT = 40;
const WALL_THICKNESS = 1.2;

// Build base and walls
let box = new Workplane("XY").box(LENGTH, WIDTH, WALL_THICKNESS);

const leftWall = new Workplane("XY")
    .box(WALL_THICKNESS, WIDTH, WALL_HEIGHT)
    .translate(-(LENGTH - WALL_THICKNESS) / 2, 0, WALL_THICKNESS);

const rightWall = new Workplane("XY")
    .box(WALL_THICKNESS, WIDTH, WALL_HEIGHT)
    .translate((LENGTH - WALL_THICKNESS) / 2, 0, WALL_THICKNESS);

const backWall = new Workplane("XY")
    .box(LENGTH - 2 * WALL_THICKNESS, WALL_THICKNESS, WALL_HEIGHT)
    .translate(0, (WIDTH - WALL_THICKNESS) / 2, WALL_THICKNESS);

box = box.union(leftWall).union(rightWall).union(backWall);

// Edge treatments first
box = box.faces("<Z").edges().chamfer(0.5);
box = box.fillet(0.3);

// Cut pattern last (for performance)
box = box.cutPattern({
    sides: 6,
    wallThickness: 1,
    border: 2,
    size: 5,
    cutFromZ: WALL_THICKNESS + 1,
    depth: WALL_THICKNESS + 2
});

box.color("#3498db");
```

---

## See Also

- [User Guide](./user-guide.md) - Interface walkthrough
- Example models in the file selector
