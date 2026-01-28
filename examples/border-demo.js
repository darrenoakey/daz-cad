// Border Demo - Test polygon offset by cutting borders into shapes
// Creates a 3x3 grid of different shapes with cutBorder applied

const BORDER = 3;  // Change this value to test different border widths

// Grid settings
const SIZE = 20;
const HEIGHT = 4;
const SPACING = 30;

// Colors for each shape
const colors = [
    "#e74c3c", "#3498db", "#2ecc71",
    "#f39c12", "#9b59b6", "#1abc9c",
    "#e67e22", "#34495e", "#c0392b"
];

// Create 9 different base shapes (3x3 grid)
const baseShapes = [
    // Row 1: Basic shapes
    new Workplane("XY").cylinder(SIZE/2, HEIGHT),           // Circle
    new Workplane("XY").box(SIZE, SIZE, HEIGHT),            // Square
    new Workplane("XY").polygonPrism(6, SIZE, HEIGHT),      // Hexagon

    // Row 2: More polygons
    new Workplane("XY").polygonPrism(3, SIZE, HEIGHT),      // Triangle
    new Workplane("XY").polygonPrism(5, SIZE, HEIGHT),      // Pentagon
    new Workplane("XY").polygonPrism(8, SIZE, HEIGHT),      // Octagon

    // Row 3: Rectangles
    new Workplane("XY").box(SIZE * 1.5, SIZE * 0.7, HEIGHT),// Wide rectangle
    new Workplane("XY").box(SIZE * 0.7, SIZE * 1.5, HEIGHT),// Tall rectangle
    new Workplane("XY").polygonPrism(12, SIZE, HEIGHT),     // Dodecagon
];

// Apply cutBorder to each shape
const assembly = new Assembly();

for (let i = 0; i < baseShapes.length; i++) {
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = (col - 1) * SPACING;
    const y = (1 - row) * SPACING;

    // Cut out the center, leaving just a border frame
    const withBorder = baseShapes[i].faces(">Z").cutBorder({
        width: BORDER
    });

    const positioned = withBorder.translate(x, y, 0).color(colors[i]);
    assembly.add(positioned);
}

const result = assembly;
result;
